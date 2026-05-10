"""Local operator UI routes."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

UI_ASSET_DIR = Path(__file__).resolve().parents[2] / "ui"

router = APIRouter(tags=["ui"])


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the local operator UI."""
    return FileResponse(UI_ASSET_DIR / "index.html")
