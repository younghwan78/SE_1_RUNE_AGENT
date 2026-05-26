"""Smoke check for the SoC Knowledge Streamlit UI seed."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

LIVE_ACCEPTANCE_CHECKS = [
    "two_browser_sessions",
    "session_isolation",
    "source_link_present",
    "source_link_clickable",
    "feedback_form_available",
]


def main() -> int:
    args = _parse_args()
    payload = {
        "status": "passed",
        "mode": "live" if args.live else "dry_run" if args.dry_run else "inspection",
        "api_only": True,
        "entrypoint": "src/req_tracker/soc_ui/streamlit_app.py",
        "modules": [
            "req_tracker.soc_ui.api_client",
            "req_tracker.soc_ui.render_answer",
            "req_tracker.soc_ui.streamlit_app",
        ],
        "endpoints": ["/api/v1/soc/query", "/api/v1/feedback"],
        "live_acceptance": {
            "checks": LIVE_ACCEPTANCE_CHECKS,
            "requires_explicit_live_flag": True,
        },
        "streamlit_available": importlib.util.find_spec("streamlit") is not None,
    }
    try:
        for module_name in payload["modules"]:
            importlib.import_module(str(module_name))
    except Exception as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)
        _emit(payload, args.format)
        return 1
    if args.live:
        live_payload = _run_live_acceptance(
            ui_url=args.ui_url,
            query_a=args.query_a,
            query_b=args.query_b,
            timeout_seconds=args.timeout_seconds,
        )
        payload["live_acceptance"].update(live_payload)
        payload["status"] = live_payload["status"]
        _emit(payload, args.format)
        return 0 if live_payload["status"] == "passed" else 1
    entrypoint = Path(payload["entrypoint"])
    if not entrypoint.exists():
        payload["status"] = "failed"
        payload["error"] = f"missing entrypoint: {entrypoint}"
        _emit(payload, args.format)
        return 1
    _emit(payload, args.format)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect modules without HTTP calls.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run Playwright against a live Streamlit UI. Requires --ui-url.",
    )
    parser.add_argument("--ui-url", default="")
    parser.add_argument(
        "--query-a",
        default="SOC-N-1 Camera Performance 이슈를 보여줘",
    )
    parser.add_argument(
        "--query-b",
        default="SOC-N-2 Power Memory 관련 항목을 보여줘",
    )
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def _run_live_acceptance(
    *,
    ui_url: str,
    query_a: str,
    query_b: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    if not ui_url:
        return {
            "status": "failed",
            "error": "--ui-url is required when --live is set",
        }
    script = _live_playwright_script()
    with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False, encoding="utf-8") as handle:
        handle.write(script)
        script_path = Path(handle.name)
    env = os.environ.copy()
    env.update(
        {
            "SOC_UI_SMOKE_QUERY_A": query_a,
            "SOC_UI_SMOKE_QUERY_B": query_b,
            "SOC_UI_SMOKE_TIMEOUT_MS": str(int(timeout_seconds * 1000)),
            "SOC_UI_SMOKE_URL": ui_url,
        }
    )
    npx_command = _npx_command()
    if npx_command is None:
        return {
            "status": "failed",
            "error": "npx is required for --live Playwright UI smoke",
        }
    try:
        completed = subprocess.run(
            [npx_command, "--yes", "--package", "playwright", "node", str(script_path)],
            check=False,
            capture_output=True,
            env=env,
            text=True,
            timeout=timeout_seconds + 30.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": str(exc)}
    finally:
        script_path.unlink(missing_ok=True)
    stdout = completed.stdout.strip()
    if completed.returncode != 0:
        return {
            "status": "failed",
            "error": completed.stderr.strip() or stdout or f"exit {completed.returncode}",
        }
    try:
        loaded = json.loads(stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return {
            "status": "failed",
            "error": f"invalid Playwright smoke output: {exc}",
            "stdout": stdout[-1000:],
        }
    if not isinstance(loaded, dict):
        return {"status": "failed", "error": "Playwright smoke output must be an object"}
    return loaded


def _npx_command() -> str | None:
    return shutil.which("npx")


def _live_playwright_script() -> str:
    return textwrap.dedent(
        r"""
        const path = require("path");

        function resolvePlaywrightModulePath() {
          const pathEntries = (process.env.PATH || "").split(path.delimiter);
          const npxBinPath = pathEntries.find((entry) =>
            /[\\/]node_modules[\\/]\.bin$/i.test(entry)
          );
          if (!npxBinPath) {
            throw new Error("unable_to_resolve_playwright_from_npx_path");
          }
          return path.join(path.dirname(npxBinPath), "playwright");
        }

        const playwrightModulePath = resolvePlaywrightModulePath();
        const { chromium } = require(playwrightModulePath);

        const uiUrl = process.env.SOC_UI_SMOKE_URL;
        const queryA = process.env.SOC_UI_SMOKE_QUERY_A;
        const queryB = process.env.SOC_UI_SMOKE_QUERY_B;
        const timeoutMs = Number(process.env.SOC_UI_SMOKE_TIMEOUT_MS || "30000");
        const checks = [
          "two_browser_sessions",
          "session_isolation",
          "source_link_present",
          "source_link_clickable",
          "feedback_form_available",
        ];

        async function runSession(browser, label, query) {
          const context = await browser.newContext();
          const page = await context.newPage();
          await page.goto(uiUrl, { waitUntil: "domcontentloaded", timeout: timeoutMs });
          const input = page.getByPlaceholder(
            "Ask about project, V-level, concern, component, or lifecycle"
          );
          await input.waitFor({ timeout: timeoutMs });
          await input.fill(query);
          await page.keyboard.press("Enter");
          await page.getByText("Confidence:", { exact: false }).waitFor({ timeout: timeoutMs });
          const sourceLinkLocator = page.locator("a[href^='http']");
          await sourceLinkLocator.first().waitFor({ timeout: timeoutMs });
          const sourceLinks = await sourceLinkLocator.evaluateAll((links) =>
            links.map((link) => ({
              href: link.href,
              label: (link.textContent || "").trim(),
            }))
          );
          if (sourceLinks.length < 1) {
            throw new Error(`${label}:missing_source_link`);
          }
          await sourceLinkLocator.first().click({ trial: true, timeout: timeoutMs });
          await page.getByText("Feedback", { exact: true }).waitFor({ timeout: timeoutMs });
          return { context, page, query, sourceLinks };
        }

        (async () => {
          const browser = await chromium.launch({ headless: true });
          try {
            const sessionA = await runSession(browser, "session_a", queryA);
            const sessionB = await runSession(browser, "session_b", queryB);
            if (await sessionA.page.getByText(queryB, { exact: false }).count() > 0) {
              throw new Error("session_a_leaked_session_b_query");
            }
            if (await sessionB.page.getByText(queryA, { exact: false }).count() > 0) {
              throw new Error("session_b_leaked_session_a_query");
            }
            console.log(JSON.stringify({
              status: "passed",
              checks,
              sessions: [
                { name: "session_a", source_link_count: sessionA.sourceLinks.length },
                { name: "session_b", source_link_count: sessionB.sourceLinks.length },
              ],
            }));
            await sessionA.context.close();
            await sessionB.context.close();
          } finally {
            await browser.close();
          }
        })().catch((error) => {
          console.error(error && error.stack ? error.stack : String(error));
          process.exit(1);
        });
        """
    ).strip()


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
