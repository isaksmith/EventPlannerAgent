from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastmcp.utilities.lifespan import combine_lifespans

from app.config import get_settings
from app.mcp.server import mcp_app
from app.routes.admin import router as admin_router
from app.routes.archive import router as archive_router
from app.routes.assets import router as assets_router
from app.routes.dashboard import router as dashboard_router
from app.routes.sites import router as sites_router
from app.webhooks.poke import router as poke_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("OrchestrateAI backend starting (env=%s)", settings.app_env)
    yield
    logger.info("OrchestrateAI backend shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    Path(settings.build_output_dir).mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="OrchestrateAI",
        description="SMS event planning orchestration backend",
        version="0.1.0",
        lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Marquee API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1.5rem; line-height: 1.5; color: #1b1a17; }
    h1 { font-size: 1.5rem; }
    a { color: #b05e40; }
    code { background: #f4f0ea; padding: 0.1rem 0.35rem; border-radius: 4px; }
    li { margin: 0.5rem 0; }
  </style>
</head>
<body>
  <h1>Marquee backend</h1>
  <p>This port is the <strong>API</strong>, not the planning dashboard.</p>
  <ul>
    <li><strong>Dashboard (UI):</strong> <a href="http://localhost:5173">http://localhost:5173</a></li>
    <li><strong>Built event sites:</strong> <a href="/sites">/sites</a> (e.g. <a href="/sites/phone_dashboard-demo/">/sites/phone_dashboard-demo/</a>)</li>
    <li><strong>Health:</strong> <a href="/health">/health</a></li>
  </ul>
</body>
</html>"""

    app.include_router(poke_router)
    app.include_router(dashboard_router)
    app.include_router(archive_router)
    app.include_router(assets_router)
    app.include_router(admin_router)
    app.include_router(sites_router)
    app.mount("/mcp", mcp_app)
    return app


app = create_app()
