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
