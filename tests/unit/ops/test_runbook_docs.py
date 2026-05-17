"""Operations runbook documentation tests."""

from pathlib import Path


def test_incident_response_runbook_covers_required_operations() -> None:
    runbook = Path("docs/runbooks/INCIDENT_RESPONSE.md")

    assert runbook.exists()

    content = runbook.read_text(encoding="utf-8").lower()
    for required in [
        "incident severity",
        "first 15 minutes",
        "run failure triage",
        "source sync failure",
        "model gateway incident",
        "approval or graph commit incident",
        "security or masking incident",
        "rollback",
        "evidence to preserve",
        "post-incident review",
    ]:
        assert required in content


def test_ubuntu_runbook_covers_handoff_bundle_workflow() -> None:
    runbook = Path("README_ubuntu.md")

    assert runbook.exists()

    content = runbook.read_text(encoding="utf-8")
    for required in [
        "ops/rehearsal/build_handoff_bundle.py",
        "--run-local-gates",
        "ops/rehearsal/validate_handoff_bundle.py",
        "manual-evidence-template coverage",
    ]:
        assert required in content


def test_readme_handoff_examples_match_final_audit_commands() -> None:
    readme = Path("README.md")
    ubuntu_runbook = Path("README_ubuntu.md")

    assert readme.exists()
    assert ubuntu_runbook.exists()

    content = _normalize_runbook_commands(
        f"{readme.read_text(encoding='utf-8')}\n{ubuntu_runbook.read_text(encoding='utf-8')}"
    )
    for required in [
        (
            "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
            "--env-file ops/rehearsal/staging.env.example "
            "--evidence-file ops/rehearsal/production_readiness_evidence.example.json "
            "--run-local-gates --output-dir .local_artifacts/staging-handoff-bundle"
        ),
        (
            "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
            "--env-file /secure/path/staging.env "
            "--evidence-file /secure/path/production_readiness_evidence.json "
            "--run-local-gates --output-dir /secure/path/rune_handoff_bundle"
        ),
        (
            "uv run python ops/rehearsal/check_production_readiness.py "
            "--run-local-gates --env-file /secure/path/staging.env "
            "--evidence-file /secure/path/production_readiness_evidence.json"
        ),
    ]:
        assert required in content


def _normalize_runbook_commands(content: str) -> str:
    return " ".join(
        content.replace("`", " ")
        .replace("\\", " ")
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )
