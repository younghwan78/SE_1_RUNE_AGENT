"""API authentication and RBAC helpers."""

from dataclasses import dataclass

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


def current_user(
    request: Request,
) -> UserContext:
    """Resolve current API user from local mode or API-key headers."""
    settings = request.app.state.settings
    api_key = request.headers.get("x-rune-api-key")
    user_id = request.headers.get("x-rune-user")
    role_header = request.headers.get("x-rune-role")
    if settings.auth_mode == "local":
        return UserContext(user_id=user_id or "local", role=role_header or "admin")
    if settings.auth_mode != "api_key":
        raise HTTPException(status_code=500, detail=f"unsupported AUTH_MODE: {settings.auth_mode}")
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API_KEY is required for AUTH_MODE=api_key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")
    role = role_header or "viewer"
    if role not in ROLE_ORDER:
        raise HTTPException(status_code=403, detail="unknown role")
    return UserContext(user_id=user_id or "api_key_user", role=role)


def require_role(request: Request, minimum_role: str) -> UserContext:
    """Require a minimum role for a sensitive endpoint."""
    user = current_user(request)
    if ROLE_ORDER[user.role] < ROLE_ORDER[minimum_role]:
        raise HTTPException(status_code=403, detail="insufficient role")
    return user
