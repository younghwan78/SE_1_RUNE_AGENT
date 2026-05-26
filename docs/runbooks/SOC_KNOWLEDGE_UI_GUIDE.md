# SoC Knowledge UI Guide

This guide is for running and checking the PoC Streamlit UI through the FastAPI boundary.
The UI must not call the database, source systems, or Claude Code subprocess directly.

## Boundaries

- Query endpoint: `/api/v1/soc/query`
- Feedback endpoint: `/api/v1/feedback`
- UI entrypoint: `src/req_tracker/soc_ui/streamlit_app.py`
- Live UI smoke: `ops/ui/smoke_soc_streamlit_ui.py`

Do not put secrets, tokens, passwords, DSNs, source URLs with credentials, or internal
endpoint credentials in this guide, command output, screenshots, or issue reports.

## Environment

Set the API base URL for the Streamlit process:

```powershell
$env:SOC_UI_API_BASE_URL = "http://127.0.0.1:18080"
```

Optional operator identity headers:

```powershell
$env:RUNE_USER = "architect_01"
$env:RUNE_ROLE = "developer"
$env:RUNE_API_KEY = "<set only in your local shell>"
```

## Local Run

Start FastAPI:

```powershell
uv run uvicorn req_tracker.api.app:create_app --factory --host 127.0.0.1 --port 18080
```

Start Streamlit:

```powershell
uv run streamlit run src/req_tracker/soc_ui/streamlit_app.py --server.address 127.0.0.1 --server.port 18580
```

Open:

```text
http://127.0.0.1:18580
```

## Smoke Checks

Dry-run import and API-boundary check:

```powershell
uv run python ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json
```

Live browser check after FastAPI and Streamlit are running:

```powershell
uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url http://127.0.0.1:18580 --format json --timeout-seconds 45
```

The live smoke should report these checks:

- `two_browser_sessions`
- `session_isolation`
- `source_link_present`
- `source_link_clickable`
- `feedback_form_available`

## Manual Acceptance

Use one question from the seed set, for example:

```text
Camera shot 성능 이슈는 무엇이 있었나?
```

Confirm:

- The answer card renders with a confidence value.
- Every answer item has at least one source link.
- Timeline rows render when the answer contains lifecycle events.
- The reasoning log toggle shows a backend-owned reference, not raw local prompts.
- Feedback submission reaches `/api/v1/feedback` and returns a recorded message.
- A second browser session does not show the first session's query text.

## Target Environment Run

Use target ports assigned by the operator, then repeat the same checks with the target URL:

```powershell
$env:SOC_UI_API_BASE_URL = "http://<api-host>:<api-port>"
uv run streamlit run src/req_tracker/soc_ui/streamlit_app.py --server.address 127.0.0.1 --server.port <ui-port>
uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url http://127.0.0.1:<ui-port> --format json --timeout-seconds 45
```

Keep PostgreSQL, source-system credentials, and model credentials outside browser-visible state.
Target evidence should record only pass/fail, counts, source-link presence, and masked endpoint status.

## Known Remaining Gaps

- Target environment repeated live UI evidence is still required.
- Real source URLs become meaningful only after Stage G source access is approved.
- Actual Claude Code `--live` quality evidence is tracked by `ops/evals/run_soc_claude_quality_gate.py`.
- Target DB storage-backed retrieval evidence is tracked by `ops/rehearsal/run_soc_live_storage_rehearsal.py`.
