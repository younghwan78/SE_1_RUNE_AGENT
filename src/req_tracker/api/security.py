"""API authentication and RBAC helpers."""

from dataclasses import dataclass
from hmac import compare_digest
from typing import Any

from fastapi import HTTPException, Request

ROLE_ORDER = {
    "viewer": 10,
    "developer": 20,
    "operator": 30,
    "admin": 40,
}


@dataclass(frozen=True)
class UserContext:
    """Authenticated API user context."""

    user_id: str
    role: str
    project_keys: tuple[str, ...] = ("*",)


def current_user(
    request: Request,
) -> UserContext:
    """Resolve current API user from local, API-key, or trusted-proxy headers."""
    settings = request.app.state.settings
    api_key = request.headers.get("x-rune-api-key")
    user_id = request.headers.get("x-rune-user")
    role_header = request.headers.get("x-rune-role")
    project_header = request.headers.get("x-rune-projects")
    project_keys = _parse_project_keys(project_header)
    if settings.auth_mode == "local":
        return UserContext(
            user_id=user_id or "local",
            role=role_header or "admin",
            project_keys=project_keys,
        )
    if settings.auth_mode == "trusted_proxy":
        return _trusted_proxy_user(
            settings=settings,
            request=request,
            user_id=user_id,
            role_header=role_header,
            project_keys=project_keys,
        )
    if settings.auth_mode != "api_key":
        raise HTTPException(status_code=500, detail=f"unsupported AUTH_MODE: {settings.auth_mode}")
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API_KEY is required for AUTH_MODE=api_key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")
    role = role_header or "viewer"
    if role not in ROLE_ORDER:
        raise HTTPException(status_code=403, detail="unknown role")
    return UserContext(
        user_id=user_id or "api_key_user",
        role=role,
        project_keys=project_keys,
    )


def _trusted_proxy_user(
    *,
    settings: Any,
    request: Request,
    user_id: str | None,
    role_header: str | None,
    project_keys: tuple[str, ...],
) -> UserContext:
    """Resolve a user from headers injected by a trusted SSO/OIDC proxy."""
    if not settings.trusted_proxy_secret:
        raise HTTPException(
            status_code=500,
            detail="TRUSTED_PROXY_SECRET is required for AUTH_MODE=trusted_proxy",
        )
    provided_secret = request.headers.get("x-rune-trusted-secret")
    if not provided_secret or not compare_digest(provided_secret, settings.trusted_proxy_secret):
        raise HTTPException(status_code=401, detail="invalid trusted proxy secret")
    if not user_id:
        raise HTTPException(status_code=401, detail="trusted proxy user header is required")
    role = _trusted_role_from_headers(
        role_header=role_header,
        group_header=request.headers.get("x-rune-groups"),
        group_role_map=settings.trusted_group_role_map,
        default_role=settings.trusted_default_role,
    )
    return UserContext(user_id=user_id, role=role, project_keys=project_keys)


def _trusted_role_from_headers(
    *,
    role_header: str | None,
    group_header: str | None,
    group_role_map: dict[str, str],
    default_role: str,
) -> str:
    groups = _parse_header_values(group_header)
    mapped_roles = [
        group_role_map[group]
        for group in groups
        if group in group_role_map
    ]
    if mapped_roles:
        role = max(mapped_roles, key=lambda item: ROLE_ORDER.get(item, -1))
    else:
        role = role_header or default_role
    if role not in ROLE_ORDER:
        raise HTTPException(status_code=403, detail="unknown role")
    return role


def require_role(request: Request, minimum_role: str) -> UserContext:
    """Require a minimum role for a sensitive endpoint."""
    user = current_user(request)
    if ROLE_ORDER[user.role] < ROLE_ORDER[minimum_role]:
        raise HTTPException(status_code=403, detail="insufficient role")
    return user


def require_project(
    request: Request,
    project_key: str | None,
    minimum_role: str = "viewer",
) -> UserContext:
    """Require role and project-level access for a project-scoped operation."""
    user = require_role(request, minimum_role)
    if project_key is None:
        return user
    if "*" not in user.project_keys and project_key not in user.project_keys:
        raise HTTPException(status_code=403, detail="project access denied")
    return user


def _parse_project_keys(project_header: str | None) -> tuple[str, ...]:
    project_keys = _parse_header_values(project_header)
    return project_keys or ("*",)


def _parse_header_values(header: str | None) -> tuple[str, ...]:
    if not header:
        return ()
    return tuple(item.strip() for item in header.split(",") if item.strip())
