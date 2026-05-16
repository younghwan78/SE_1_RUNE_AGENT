"""Decision/email export rehearsal tests."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def test_decision_email_rehearsal_reports_missing_export_path() -> None:
    module = _load_module()

    report = module.run_decision_email_export_rehearsal({})

    assert report["passed"] is False
    assert report["status"] == "missing_config"
    assert "RUNE_EMAIL_EXPORT_PATH" in report["missing"]
    assert report["config"]["export_path"] == "<unset>"


def test_decision_email_rehearsal_allows_only_approved_decisions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    export_path = tmp_path / "decision_email.jsonl"
    export_path.write_text(
        "\n".join(
            [
                json.dumps(
                    _artifact(
                        "MAIL-DEC-1",
                        "email",
                        labels=["decision"],
                        metadata={
                            "mbse_type": "Decision",
                            "decision_source_approved": True,
                        },
                    )
                ),
                json.dumps(
                    _artifact(
                        "MAIL-FULL-1",
                        "email",
                        labels=["mailbox"],
                        metadata={"mbse_type": "Decision"},
                    )
                ),
                json.dumps(
                    _artifact(
                        "CONF-LEAK-1",
                        "confluence",
                        labels=["decision"],
                        metadata={"mbse_type": "Decision"},
                    )
                ),
                json.dumps(
                    _artifact(
                        "MAIL-SENSITIVE-1",
                        "email",
                        labels=["decision"],
                        metadata={
                            "mbse_type": "Decision",
                            "decision_source_approved": True,
                            "manual_review_required": True,
                        },
                    )
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = module.run_decision_email_export_rehearsal({}, export_path=export_path)

    assert report["passed"] is True
    assert report["artifact_count"] == 1
    assert report["skipped_count"] == 2
    assert report["manual_review_count"] == 1
    assert report["config"]["export_path"] == "<set>"
    assert report["artifacts"][0]["external_id"] == "MAIL-DEC-1"
    assert report["warnings"] == [
        "decision_email_artifact_skipped:MAIL-FULL-1",
        "decision_email_artifact_skipped:CONF-LEAK-1",
        "decision_email_manual_review_required:MAIL-SENSITIVE-1",
    ]


def _artifact(
    external_id: str,
    source_type: str,
    *,
    labels: list[str],
    metadata: dict[str, object],
) -> dict[str, object]:
    return {
        "external_id": external_id,
        "source_type": source_type,
        "source_url": f"export://{source_type}/{external_id}",
        "project_key": "RUNE_CAM_ALPHA",
        "title": external_id,
        "body_text": f"{external_id} decision body",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "labels": labels,
        "links": [],
        "metadata": metadata,
        "access_scope": ["RUNE_CAM_ALPHA"],
        "data_classification": "public_internal",
    }


def _load_module() -> ModuleType:
    module_path = Path("ops/source/rehearse_decision_email_export.py")
    spec = importlib.util.spec_from_file_location("rehearse_decision_email_export", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
