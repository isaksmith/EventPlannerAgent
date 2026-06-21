from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _safe_asset_path(slug: str, filename: str) -> Path:
    root = Path(get_settings().assets_output_dir) / slug
    target = (root / filename).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise HTTPException(status_code=404, detail="Invalid path")
    return target


@router.get("/{slug}/{filename}")
async def serve_session_asset(slug: str, filename: str) -> FileResponse:
    """Serve generated brand assets (Midjourney logo/hero, promo clip) for the dashboard."""
    path = _safe_asset_path(slug, filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(path)
