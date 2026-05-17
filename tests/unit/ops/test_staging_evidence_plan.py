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
    assert gates["postgres_state_store"]["missing_env"] == ["STATE_STORE"]
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


def test_staging_evidence_plan_loads_env_file_without_leaking_secret(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    env_path = tmp_path / "staging.env"
    env_path.write_text(
        "\n".join(
            [
                "STATE_STORE=postgres",
                "POSTGRES_DSN=postgresql://rune:secret@db/rune_agent",
                "GRAPH_BACKEND=neo4j",
                "NEO4J_URI=bolt://neo4j:7687",
                "NEO4J_USERNAME=neo4j",
                "NEO4J_PASSWORD=secret",
            ]
        ),
        encoding="utf-8",
    )

    env = module.load_plan_env(env_path)
    plan = module.build_staging_evidence_plan(env)

    gates = {gate["check_id"]: gate for gate in plan["gates"]}
    assert "postgres_state_store" not in gates
    assert "neo4j_graph_backend" not in gates
    assert "qdrant_vector_backend" in gates
    assert "rune:secret" not in str(plan)
    assert "bolt://neo4j" not in str(plan)


def test_staging_evidence_plan_markdown_is_operator_readable() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan({})
    markdown = module.render_markdown(plan)

    assert "# Staging Evidence Collection Plan" in markdown
    assert "## Final Validation" in markdown
    assert "## company_model_gateway_rehearsal" in markdown
    assert "- Next action:" in markdown
    assert "- Missing env:" in markdown
    assert (
        "Run ops/model_gateway/rehearse_model_gateway.py against the "
        "company-approved model provider sandbox."
    ) in markdown
    assert "`uv run python ops/model_gateway/rehearse_model_gateway.py`" in markdown
    assert "--evidence-file <reviewed-evidence.json>" in markdown
    assert "TODO" not in markdown


def test_staging_evidence_plan_includes_final_validation_commands() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan({})

    assert plan["final_validation_commands"] == [
        (
            "uv run python ops/rehearsal/check_production_readiness.py "
            "--run-local-gates --env-file <staging.env> "
            "--evidence-file <reviewed-evidence.json>"
        ),
        (
            "uv run python ops/rehearsal/check_goal_completion.py "
            "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
            "--run-local-gates"
        ),
        (
            "uv run python ops/rehearsal/build_handoff_bundle.py "
            "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
            "--run-local-gates --output-dir <handoff-bundle-dir>"
        ),
        "uv run python ops/rehearsal/validate_handoff_bundle.py <handoff-bundle-dir>",
        (
            "uv run python ops/rehearsal/assert_local_handoff_complete.py "
            "<handoff-bundle-dir>"
        ),
    ]


def test_final_validation_commands_have_single_shared_source() -> None:
    commands_module = _load_module_from_path(
        "final_validation_commands",
        "ops/rehearsal/final_validation_commands.py",
    )
    staging_plan = _load_module()
    goal_completion = _load_module_from_path(
        "check_goal_completion",
        "ops/rehearsal/check_goal_completion.py",
    )

    plan = staging_plan.build_staging_evidence_plan({})
    report = goal_completion.build_goal_completion_audit({})
    company_item = {
        item["criterion_id"]: item for item in report["prompt_to_artifact_checklist"]
    }["company_staging_readiness"]

    assert tuple(plan["final_validation_commands"]) == commands_module.FINAL_VALIDATION_COMMANDS
    assert tuple(company_item["commands"][1:]) == commands_module.FINAL_VALIDATION_COMMANDS


def test_staging_evidence_plan_applies_reviewed_manual_evidence() -> None:
    module = _load_module()
    checker = _load_checker_module()

    plan = module.build_staging_evidence_plan(
        {},
        manual_evidence=[
            checker.ManualEvidence(
                check_id="local_regression_gates",
                status="passed",
                summary="Local gates passed in reviewed CI.",
                evidence=["github-actions:CI:run-25981321130"],
            )
        ],
    )

    gates = {gate["check_id"]: gate for gate in plan["gates"]}
    assert "local_regression_gates" not in gates


def test_staging_evidence_plan_guides_every_unresolved_gate() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan({})

    for gate in plan["gates"]:
        assert gate["commands"], gate["check_id"]
        assert gate["required_evidence"], gate["check_id"]
        assert gate["docs"], gate["check_id"]


def test_staging_evidence_plan_doc_refs_exist() -> None:
    module = _load_module()

    plan = module.build_staging_evidence_plan({})

    for gate in plan["gates"]:
        for doc_ref in gate["docs"]:
            path_text, _, anchor = doc_ref.partition("#")
            path = Path(path_text)
            assert path.exists(), f"{gate['check_id']} references missing doc {doc_ref}"
            if anchor:
                anchors = _markdown_anchors(path)
                assert anchor in anchors, (
                    f"{gate['check_id']} references missing anchor {doc_ref}; "
                    f"available={sorted(anchors)}"
                )


def _load_module() -> ModuleType:
    return _load_module_from_path(
        "build_staging_evidence_plan",
        "ops/rehearsal/build_staging_evidence_plan.py",
    )


def _load_module_from_path(name: str, path: str) -> ModuleType:
    module_path = Path(path)
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_checker_module() -> ModuleType:
    module_path = Path("ops/rehearsal/check_production_readiness.py")
    spec = importlib.util.spec_from_file_location("check_production_readiness", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if heading:
            anchors.add(_github_anchor(heading))
    return anchors


def _github_anchor(heading: str) -> str:
    result: list[str] = []
    previous_dash = False
    for character in heading.lower():
        if character.isalnum():
            result.append(character)
            previous_dash = False
            continue
        if character.isspace() or character == "-":
            if not previous_dash:
                result.append("-")
                previous_dash = True
    return "".join(result).strip("-")
