"""Stage G checks for SoC real-source switch readiness."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_stage_g_acceptance_yaml_tracks_real_source_switch_gap_items() -> None:
    payload = yaml.safe_load((ROOT / "eval/stages/G.yaml").read_text(encoding="utf-8"))
    payload_text = str(payload)

    assert payload["stage"] == "G"
    assert payload["name"] == "Real Data Switch"
    assert {
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",
        "G6",
        "G7",
        "G8",
        "G9",
        "G10",
    } == {item["id"] for item in payload["subgoals"]}
    assert ".claude/skills/rune-source-jira/SKILL.md" in payload_text
    assert ".claude/skills/rune-source-confluence/SKILL.md" in payload_text
    assert ".claude/skills/rune-source-email/SKILL.md" in payload_text
    assert "ops/rehearsal/run_soc_real_source_switch_rehearsal.py" in payload_text
    assert "fixture_to_real_switch_ready" in payload_text
    assert "POSTGRES_TEST_DSN=<target>" in payload_text
    assert "MCP" not in payload_text
