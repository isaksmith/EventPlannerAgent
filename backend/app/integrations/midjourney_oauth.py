from __future__ import annotations

import logging
import webbrowser

from fastmcp.client.auth.oauth import OAuth

logger = logging.getLogger(__name__)


class BrowserOAuth(OAuth):
    """OAuth that opens the browser without a pre-flight GET (Midjourney returns 403)."""

    async def redirect_handler(self, authorization_url: str) -> None:
        logger.info("Midjourney OAuth URL: %s", authorization_url)
        print(f"\nIf no browser opens, visit:\n{authorization_url}\n")
        webbrowser.open(authorization_url)
