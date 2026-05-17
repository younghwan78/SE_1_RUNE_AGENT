"""Production handoff bundle tests."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_handoff_bundle_writes_required_artifacts_without_secrets(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    env_path = tmp_path / "staging.env"
    env_path.write_text(
        "\n".join(
            [
                "STATE_STORE=postgres",
                "POSTGRES_DSN=postgresql://rune:secret-value@db/rune_agent",
                "GRAPH_BACKEND=neo4j",
                "NEO4J_URI=bolt://neo4j:7687",
                "NEO4J_USERNAME=neo4j",
                "NEO4J_PASSWORD=secret-value",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "handoff"

    manifest = module.build_handoff_bundle(
        output_dir,
        env_file=env_path,
        run_local_gates=False,
    )

    expected_files = {
        "manifest.json",
        "staging-evidence-plan.md",
        "manual-evidence-template.json",
        "production-readiness-report.json",
        "goal-completion-report.json",
    }
    assert {path.name for path in output_dir.iterdir()} == expected_files
    assert manifest["schema_version"] == "v1"
    assert manifest["env_file"] == "staging.env"
    assert manifest["run_local_gates"] is False
    assert manifest["goal_complete"] is False
    assert manifest["readiness_passed"] is False
    assert set(manifest["artifacts"]) == expected_files - {"manifest.json"}
    assert manifest["remaining_blocker_count"] == manifest["goal_summary"][
        "remaining_blocker_count"
    ]
    assert manifest["remaining_blockers"]
    assert {
        "blocker_id",
        "status",
        "next_action",
    } <= set(manifest["remaining_blockers"][0])
    assert manifest == json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "secret-value" not in _read_bundle(output_dir)
    assert "postgresql://rune" not in _read_bundle(output_dir)


def test_handoff_bundle_can_include_reviewed_evidence_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "release-owner@example.com",
          "reviewed_at": "2026-05-12T00:00:00Z",
          "checks": [
            {
              "check_id": "local_regression_gates",
              "status": "passed",
              "summary": "Local gates passed in CI.",
              "evidence": ["github-actions:CI:run-1"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    output_dir = tmp_path / "handoff"

    manifest = module.build_handoff_bundle(
        output_dir,
        evidence_file=evidence_path,
        run_local_gates=False,
    )

    readiness = json.loads(
        (output_dir / "production-readiness-report.json").read_text(encoding="utf-8")
    )
    assert manifest["evidence_file"] == "evidence.json"
    assert readiness["manual_evidence_count"] == 1
    assert "github-actions:CI:run-1" in _read_bundle(output_dir)


def test_handoff_bundle_cli_allows_incomplete_smoke(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    output_dir = tmp_path / "handoff"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_handoff_bundle.py",
            "--output-dir",
            str(output_dir),
            "--env-file",
            ".env.example",
            "--allow-incomplete",
        ],
    )

    assert module.main() == 0
    assert (output_dir / "manifest.json").exists()


def _read_bundle(path: Path) -> str:
    return "\n".join(
        file_path.read_text(encoding="utf-8")
        for file_path in sorted(path.iterdir())
        if file_path.is_file()
    )


def _load_module() -> ModuleType:
    module_path = Path("ops/rehearsal/build_handoff_bundle.py")
    spec = importlib.util.spec_from_file_location("build_handoff_bundle", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
