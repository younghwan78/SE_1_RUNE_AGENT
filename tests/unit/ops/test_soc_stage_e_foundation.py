"""Stage E checks for the SoC Knowledge PoC UI seed."""

import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_soc_streamlit_ui_smoke_reports_api_only_seed() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/ui/smoke_soc_streamlit_ui.py",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "passed"
    assert payload["mode"] == "dry_run"
    assert payload["api_only"] is True
    assert payload["entrypoint"] == "src/req_tracker/soc_ui/streamlit_app.py"
    assert payload["live_acceptance"]["requires_explicit_live_flag"] is True
    assert payload["live_acceptance"]["checks"] == [
        "two_browser_sessions",
        "session_isolation",
        "source_link_present",
        "source_link_clickable",
        "feedback_form_available",
    ]


def test_stage_e_acceptance_yaml_tracks_ui_gap_items() -> None:
    payload = yaml.safe_load((ROOT / "eval/stages/E.yaml").read_text(encoding="utf-8"))

    assert payload["stage"] == "E"
    assert {
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        "E8",
        "E9",
        "E10",
        "E11",
    } == {item["id"] for item in payload["subgoals"]}
    assert "src/req_tracker/soc_ui/streamlit_app.py" in str(payload)
    assert "src/req_tracker/soc_ui/api_client.py" in str(payload)
    assert "src/req_tracker/soc_ui/render_answer.py" in str(payload)
    assert "/api/v1/soc/query" in str(payload)
    assert "/api/v1/feedback" in str(payload)
    assert "ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json" in str(payload)
    assert "ops/rehearsal/run_full_stack_rehearsal.py" in str(payload)
    assert "docs/runbooks/SOC_KNOWLEDGE_UI_GUIDE.md" in str(payload)
    assert "ACC-E-LIVE-02" in str(payload)
    assert "ACC-E-LIVE-03" in str(payload)
    assert "ACC-E-DOC-01" in str(payload)


def test_soc_ui_usage_guide_contains_target_runbook_commands() -> None:
    guide = (ROOT / "docs/runbooks/SOC_KNOWLEDGE_UI_GUIDE.md").read_text(encoding="utf-8")

    assert "SOC_UI_API_BASE_URL" in guide
    assert "uv run uvicorn req_tracker.api.app:create_app" in guide
    assert "uv run streamlit run src/req_tracker/soc_ui/streamlit_app.py" in guide
    assert "uv run python ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json" in guide
    assert "uv run python ops/ui/smoke_soc_streamlit_ui.py --live" in guide
    assert "/api/v1/soc/query" in guide
    assert "/api/v1/feedback" in guide
    assert "Do not put secrets" in guide


def test_stage_e_streamlit_dependency_is_optional_extra() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "soc-ui" in payload["project"]["optional-dependencies"]
    assert any(
        dependency.startswith("streamlit")
        for dependency in payload["project"]["optional-dependencies"]["soc-ui"]
    )


def test_soc_streamlit_live_smoke_resolves_npx_executable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    smoke = _load_smoke_module()

    monkeypatch.setattr(
        smoke.shutil,
        "which",
        lambda name: "C:/Program Files/nodejs/npx.cmd" if name == "npx" else None,
    )

    assert smoke._npx_command() == "C:/Program Files/nodejs/npx.cmd"


def test_soc_streamlit_live_script_resolves_playwright_from_npx_path() -> None:
    smoke = _load_smoke_module()

    script = smoke._live_playwright_script()

    assert "node_modules" in script
    assert r"[\\/]\.bin" in script
    assert r"[\\/]\\.bin" not in script
    assert "sourceLinkLocator.first().waitFor" in script
    assert "require(playwrightModulePath)" in script
    assert 'require("playwright")' not in script


def _load_smoke_module() -> ModuleType:
    module_path = ROOT / "ops/ui/smoke_soc_streamlit_ui.py"
    spec = importlib.util.spec_from_file_location("smoke_soc_streamlit_ui", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
