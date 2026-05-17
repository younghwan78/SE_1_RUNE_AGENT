"""Build a production handoff bundle for company/staging release evidence.

The bundle groups the files a release owner needs for a production-readiness
review without printing or copying secret environment values.
"""

import argparse
import importlib.util
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent


def build_handoff_bundle(
    output_dir: Path,
    *,
    env_file: Path | None = None,
    evidence_file: Path | None = None,
    run_local_gates: bool = False,
) -> dict[str, Any]:
    """Write handoff artifacts to ``output_dir`` and return the manifest."""
    readiness = _load_script_module(
        "check_production_readiness",
        SCRIPT_DIR / "check_production_readiness.py",
    )
    staging_plan = _load_script_module(
        "build_staging_evidence_plan",
        SCRIPT_DIR / "build_staging_evidence_plan.py",
    )
    goal_completion = _load_script_module(
        "check_goal_completion",
        SCRIPT_DIR / "check_goal_completion.py",
    )
    env = readiness.load_env_file(env_file, os.environ) if env_file else dict(os.environ)
    manual_evidence = (
        readiness.load_manual_evidence(evidence_file) if evidence_file else []
    )

    plan = staging_plan.build_staging_evidence_plan(env)
    readiness_report = readiness.build_readiness_report(
        env,
        run_local_gates=run_local_gates,
        manual_evidence=manual_evidence,
    )
    goal_report = goal_completion.build_goal_completion_audit(
        env,
        run_local_gates=run_local_gates,
        manual_evidence=manual_evidence,
    )
    manual_template = readiness.build_manual_evidence_template(env)

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "staging-evidence-plan.md": staging_plan.render_markdown(plan) + "\n",
        "manual-evidence-template.json": _render_json(manual_template),
        "production-readiness-report.json": _render_json(readiness_report),
        "goal-completion-report.json": _render_json(goal_report),
    }
    for filename, content in artifacts.items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    manifest = {
        "schema_version": "v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "env_file": env_file.name if env_file else None,
        "evidence_file": evidence_file.name if evidence_file else None,
        "run_local_gates": run_local_gates,
        "artifacts": sorted(artifacts),
        "readiness_passed": readiness_report["passed"],
        "goal_complete": goal_report["goal_complete"],
        "readiness_summary": readiness_report["summary"],
        "goal_summary": goal_report["summary"],
    }
    (output_dir / "manifest.json").write_text(_render_json(manifest), encoding="utf-8")
    return manifest


def _render_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_script_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory that will receive the handoff bundle artifacts.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional KEY=VALUE company/staging environment file.",
    )
    parser.add_argument(
        "--evidence-file",
        type=Path,
        default=None,
        help="Optional reviewed manual evidence JSON file.",
    )
    parser.add_argument(
        "--run-local-gates",
        action="store_true",
        help="Execute local regression gates while generating reports.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Return success after writing a structurally valid incomplete bundle.",
    )
    args = parser.parse_args()
    manifest = build_handoff_bundle(
        args.output_dir,
        env_file=args.env_file,
        evidence_file=args.evidence_file,
        run_local_gates=args.run_local_gates,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["goal_complete"] or args.allow_incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
