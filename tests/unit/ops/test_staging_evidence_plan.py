"""Staging evidence collection plan tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_staging_evidence_plan_lists_unresolved_gates_without_secrets() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan(
        {
            "POSTGRES_DSN": "postgresql://user:secret@example.test/rune",
            "TRUSTED_PROXY_SECRET": "proxy-secret",
        }
    )

    assert plan["schema_version"] == "v1"
    assert plan["unresolved_count"] > 0
    gates = {gate["check_id"]: gate for gate in plan["gates"]}
    assert "postgres_state_store" in gates
    assert "company_jira_sandbox_rehearsal" in gates
    assert "POSTGRES_DSN" in " ".join(gates["postgres_state_store"]["required_env"])
    assert (
        "uv run python ops/source/rehearse_company_sources.py --source jira"
        in gates["company_jira_sandbox_rehearsal"]["commands"]
    )
    assert "proxy-secret" not in str(plan)
    assert "user:secret" not in str(plan)
    assert "postgresql://user" not in str(plan)


def test_staging_evidence_plan_includes_kubernetes_gate_when_selected() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan(
        {
            "DEPLOYMENT_TARGET": "kubernetes",
            "KUBERNETES_DEPLOYMENT": "true",
        }
    )

    gates = {gate["check_id"]: gate for gate in plan["gates"]}
    assert "kubernetes_helm_rehearsal" in gates
    assert "helm lint ops/helm/rune-agent" in gates["kubernetes_helm_rehearsal"]["commands"]


def test_staging_evidence_plan_markdown_is_operator_readable() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan({})
    markdown = module.render_markdown(plan)

    assert "# Staging Evidence Collection Plan" in markdown
    assert "## company_model_gateway_rehearsal" in markdown
    assert "`uv run python ops/model_gateway/rehearse_model_gateway.py`" in markdown
    assert "TODO" not in markdown


def _load_module() -> ModuleType:
    module_path = Path("ops/rehearsal/build_staging_evidence_plan.py")
    spec = importlib.util.spec_from_file_location("build_staging_evidence_plan", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
