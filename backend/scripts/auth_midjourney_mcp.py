#!/usr/bin/env python3
"""One-time OAuth login for official Midjourney MCP (opens browser)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import Client
from app.integrations.midjourney_oauth import BrowserOAuth
from key_value.aio.stores.disk import DiskStore

from app.config import get_settings


async def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    url = settings.midjourney_mcp_url.rstrip("/")
    oauth_dir = Path(__file__).resolve().parent.parent / "var" / "midjourney_mcp" / "oauth"
    oauth_dir.mkdir(parents=True, exist_ok=True)
    oauth = BrowserOAuth(mcp_url=url, token_storage=DiskStore(directory=str(oauth_dir)), client_name="Marquee Backend")

    print(f"Connecting to {url}")
    print("A browser window will open to log in to Midjourney (once).")

    try:
        async with Client(url, auth=oauth, timeout=600) as client:
            tools = await client.list_tools()
            print(f"Authenticated. {len(tools)} tool(s) available:")
            for tool in tools:
                print(f"  - {tool.name}")
    except Exception as exc:
        print(f"Auth failed: {exc}", file=sys.stderr)
        return 1

    print("\nSuccess. OAuth tokens saved under var/midjourney_mcp/oauth/")
    print("Enable generation in .env: MIDJOURNEY_MCP_ENABLED=true")
    print("Set MIDJOURNEY_MCP_USE_OAUTH=true to reuse OAuth from the backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
