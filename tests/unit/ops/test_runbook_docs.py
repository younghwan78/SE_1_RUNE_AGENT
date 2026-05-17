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
    local_handoff = Path("docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md")

    assert readme.exists()
    assert ubuntu_runbook.exists()
    assert local_handoff.exists()

    readme_content = _normalize_runbook_commands(readme.read_text(encoding="utf-8"))
    ubuntu_content = _normalize_runbook_commands(ubuntu_runbook.read_text(encoding="utf-8"))
    handoff_content = _normalize_runbook_commands(local_handoff.read_text(encoding="utf-8"))

    for content, required in [
        (
            readme_content,
            (
                "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
                "--env-file ops/rehearsal/staging.env.example "
                "--evidence-file ops/rehearsal/production_readiness_evidence.example.json "
                "--run-local-gates --output-dir .local_artifacts/staging-handoff-bundle"
            ),
        ),
        (
            ubuntu_content,
            (
                "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
                "--env-file /secure/path/staging.env "
                "--evidence-file /secure/path/production_readiness_evidence.json "
                "--run-local-gates --output-dir /secure/path/rune_handoff_bundle"
            ),
        ),
        (
            ubuntu_content,
            (
                "uv run python ops/rehearsal/check_production_readiness.py "
                "--run-local-gates --env-file /secure/path/staging.env "
                "--evidence-file /secure/path/production_readiness_evidence.json"
            ),
        ),
        (
            handoff_content,
            (
                "uv run python ops/rehearsal/check_production_readiness.py "
                "--run-local-gates --env-file /secure/path/staging.env "
                "--evidence-file /secure/path/production_readiness_evidence.json"
            ),
        ),
        (
            handoff_content,
            (
                "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
                "--env-file /secure/path/staging.env "
                "--evidence-file /secure/path/production_readiness_evidence.json "
                "--run-local-gates --output-dir /secure/path/rune_handoff_bundle"
            ),
        ),
        (
            readme_content,
            (
                "uv run python ops/rehearsal/assert_local_handoff_complete.py "
                ".local_artifacts/staging-handoff-bundle"
            ),
        ),
        (
            ubuntu_content,
            (
                "uv run python ops/rehearsal/assert_local_handoff_complete.py "
                "/secure/path/rune_handoff_bundle"
            ),
        ),
        (
            handoff_content,
            (
                "uv run python ops/rehearsal/assert_local_handoff_complete.py "
                "/secure/path/rune_handoff_bundle"
            ),
        ),
    ]:
        assert required in content


def test_handoff_runbooks_document_blocker_summary_manifest() -> None:
    readme = Path("README.md")
    ubuntu_runbook = Path("README_ubuntu.md")
    local_handoff = Path("docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md")

    for path in [readme, ubuntu_runbook, local_handoff]:
        content = path.read_text(encoding="utf-8")
        assert "blocker_summary" in content
        assert "local_action_required" in content
        assert "company_or_staging_evidence_required" in content
        assert "blocker_summary_mismatch" in content


def _normalize_runbook_commands(content: str) -> str:
    return " ".join(
        content.replace("`", " ")
        .replace("\\", " ")
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )
