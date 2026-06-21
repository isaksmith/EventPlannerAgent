from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_OPENCODE_AUTH = Path.home() / ".local/share/opencode/auth.json"


def resolve_openrouter_api_key(settings: Settings | None = None) -> str:
    """
    OpenRouter key from OPENROUTER_API_KEY, else OpenCode CLI auth store.
    """
    cfg = settings or get_settings()
    if cfg.openrouter_api_key.strip():
        return cfg.openrouter_api_key.strip()

    if not _OPENCODE_AUTH.is_file():
        return ""

    try:
        data = json.loads(_OPENCODE_AUTH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read OpenCode auth for OpenRouter: %s", exc)
        return ""

    if not isinstance(data, dict):
        return ""

    for provider_key in ("openrouter", "OpenRouter", "OPENROUTER"):
        entry = data.get(provider_key)
        if isinstance(entry, str) and entry.strip():
            logger.info("Using OpenRouter API key from OpenCode auth (%s)", provider_key)
            return entry.strip()
        if isinstance(entry, dict):
            for field in ("key", "apiKey", "api_key", "token", "access_token"):
                val = entry.get(field)
                if isinstance(val, str) and val.strip():
                    logger.info("Using OpenRouter API key from OpenCode auth (%s)", provider_key)
                    return val.strip()

    return ""


def openrouter_images_ready(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.openrouter_image_enabled and resolve_openrouter_api_key(cfg))
