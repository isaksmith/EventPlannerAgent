from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.integrations.openrouter_auth import openrouter_images_ready, resolve_openrouter_api_key
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Midjourney brief aspect → OpenRouter image_config.aspect_ratio
_ASPECT_MAP = {
    "1:1": "1:1",
    "3:4": "3:4",
    "4:3": "4:3",
    "16:9": "16:9",
    "9:16": "9:16",
    "2:3": "2:3",
    "3:2": "3:2",
}


def openrouter_images_configured(settings: Settings) -> bool:
    return openrouter_images_ready(settings)


def _headers(settings: Settings) -> dict[str, str]:
    api_key = resolve_openrouter_api_key(settings)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_name:
        headers["X-Title"] = settings.openrouter_app_name
    return headers


def _parse_data_url(url: str) -> tuple[bytes, str] | None:
    match = re.match(r"^data:([^;]+);base64,(.+)$", url.strip(), re.DOTALL)
    if not match:
        return None
    mime = match.group(1)
    try:
        data = base64.b64decode(match.group(2), validate=False)
    except (ValueError, TypeError):
        return None
    if not data:
        return None
    return data, mime


def _suffix_for_mime(mime: str) -> str:
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    return mapping.get(mime.lower(), ".png")


def extract_image_data_urls(response: dict[str, Any]) -> list[str]:
    """Pull base64 data URLs from an OpenRouter chat completion response."""
    urls: list[str] = []
    choices = response.get("choices") or []
    if not choices:
        return urls

    message = choices[0].get("message") or {}
    for image in message.get("images") or []:
        if not isinstance(image, dict):
            continue
        image_url = image.get("image_url") or image.get("imageUrl") or {}
        if isinstance(image_url, dict):
            url = image_url.get("url") or ""
        else:
            url = str(image_url)
        if url.startswith("data:"):
            urls.append(url)

    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") in {"image_url", "image"}:
                block = part.get("image_url") or part.get("image") or {}
                url = block.get("url") if isinstance(block, dict) else str(block)
                if url and url.startswith("data:"):
                    urls.append(url)

    return urls


def _write_image_file(data: bytes, mime: str, dest: Path) -> Path:
    dest = dest.with_suffix(_suffix_for_mime(mime))
    dest.write_bytes(data)
    return dest


async def generate_image_via_openrouter(
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    settings: Settings | None = None,
) -> tuple[bytes, str] | None:
    """Single image via OpenRouter chat completions + modalities."""
    cfg = settings or get_settings()
    if not openrouter_images_configured(cfg):
        return None

    aspect = _ASPECT_MAP.get(aspect_ratio, aspect_ratio)
    payload: dict[str, Any] = {
        "model": cfg.openrouter_image_model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": aspect},
    }

    async with httpx.AsyncClient(timeout=cfg.openrouter_image_timeout_seconds) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers=_headers(cfg),
            json=payload,
        )
        if response.status_code >= 400:
            logger.warning(
                "OpenRouter image HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )
            return None

        data_urls = extract_image_data_urls(response.json())
        if not data_urls:
            logger.warning("OpenRouter image response had no images for prompt: %s", prompt[:80])
            return None

        parsed = _parse_data_url(data_urls[0])
        if parsed is None:
            return None
        return parsed


async def generate_invite_assets_via_openrouter(
    briefs: list[tuple[str, str, str]],
    asset_dir: Path,
    settings: Settings | None = None,
) -> list[str] | None:
    """
    Generate invite PNGs via OpenRouter when Midjourney MCP is unavailable.
    briefs: (filename_stem, prompt, aspect_ratio) e.g. invite_cover, ..., 3:4
    Returns file paths on success (at least one image), else None.
    """
    cfg = settings or get_settings()
    if not openrouter_images_configured(cfg):
        return None

    asset_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    tracer = get_tracer()
    async with tracer.span(
        "openrouter.images",
        model=cfg.openrouter_image_model,
        count=len(briefs),
    ):
        for stem, prompt, aspect in briefs:
            result = await generate_image_via_openrouter(
                prompt,
                aspect_ratio=aspect,
                settings=cfg,
            )
            if result is None:
                logger.warning("OpenRouter failed for %s", stem)
                continue
            data, mime = result
            out = _write_image_file(data, mime, asset_dir / stem)
            paths.append(str(out))
            logger.info("OpenRouter saved %s (%d bytes)", out.name, len(data))

    return paths if paths else None
