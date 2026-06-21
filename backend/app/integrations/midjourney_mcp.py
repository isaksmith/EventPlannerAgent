from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastmcp import Client
from fastmcp.client.auth.oauth import OAuth

from app.config import Settings, get_settings
from app.integrations.midjourney_oauth import BrowserOAuth

logger = logging.getLogger(__name__)

IMAGINE_TOOL_CANDIDATES = ("generate_image", "imagine", "midjourney_imagine", "generate")
IMAGE_URL_RE = re.compile(
    r"https?://[^\s\)\]\"'<>]+(?:\.(?:png|jpg|jpeg|webp|gif)|cdn\.discordapp\.com[^\s\)\]\"'<>]*)",
    re.IGNORECASE,
)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_OAUTH_DIR = _BACKEND_ROOT / "var" / "midjourney_mcp" / "oauth"


def _client_auth(settings: Settings) -> str | OAuth | None:
    if settings.midjourney_mcp_token:
        return settings.midjourney_mcp_token
    if settings.midjourney_mcp_use_oauth:
        from key_value.aio.stores.disk import DiskStore

        _OAUTH_DIR.mkdir(parents=True, exist_ok=True)
        token_storage = DiskStore(directory=str(_OAUTH_DIR))
        return BrowserOAuth(
            mcp_url=settings.midjourney_mcp_url.rstrip("/"),
            token_storage=token_storage,
            client_name="Marquee Backend",
        )
    return None


def mcp_configured(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.midjourney_mcp_enabled and _client_auth(cfg))


def _collect_urls(value: Any, found: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        found.extend(IMAGE_URL_RE.findall(value))
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_urls(item, found)
        return
    if isinstance(value, list):
        for item in value:
            _collect_urls(item, found)


def extract_image_urls(result: Any) -> list[str]:
    """Pull image URLs from an MCP tool result."""
    found: list[str] = []
    if hasattr(result, "structured_content") and result.structured_content:
        _collect_urls(result.structured_content, found)
    if hasattr(result, "data") and result.data is not None:
        _collect_urls(result.data, found)
    if hasattr(result, "content") and result.content:
        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                _collect_urls(text, found)
                try:
                    _collect_urls(json.loads(text), found)
                except json.JSONDecodeError:
                    pass
    deduped: list[str] = []
    seen: set[str] = set()
    for url in found:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def extract_inline_image(result: Any) -> tuple[bytes, str] | None:
    """Read the first inline image block from an MCP tool result (preferred over CDN URLs)."""
    if not hasattr(result, "content") or not result.content:
        return None
    for block in result.content:
        if getattr(block, "type", None) != "image":
            continue
        raw = getattr(block, "data", None)
        if not raw:
            continue
        mime = getattr(block, "mimeType", None) or getattr(block, "mime_type", None) or "image/png"
        try:
            return base64.b64decode(raw), str(mime)
        except Exception:
            logger.warning("Failed to decode inline Midjourney image block")
    return None


def _suffix_for_mime(mime: str) -> str:
    normalized = mime.lower()
    if "webp" in normalized:
        return ".webp"
    if "jpeg" in normalized or "jpg" in normalized:
        return ".jpg"
    if "gif" in normalized:
        return ".gif"
    return ".png"


def _write_image_bytes(data: bytes, mime: str, dest: Path) -> Path:
    suffix = _suffix_for_mime(mime)
    final_path = dest if dest.suffix.lower() == suffix else dest.with_suffix(suffix)
    final_path.write_bytes(data)
    return final_path


def extract_resource_uri(result: Any, grid_index: int = 0) -> str | None:
    """Pick one full-resolution image from a Midjourney grid result."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        images = structured.get("images")
        if isinstance(images, list) and images:
            idx = min(grid_index, len(images) - 1)
            entry = images[idx]
            if isinstance(entry, dict):
                uri = entry.get("resource_uri")
                if uri:
                    return str(uri)

    data = getattr(result, "data", None)
    if data is not None and hasattr(data, "images"):
        images = data.images
        if images:
            idx = min(grid_index, len(images) - 1)
            entry = images[idx]
            uri = getattr(entry, "resource_uri", None)
            if uri:
                return str(uri)

    if hasattr(result, "content") and result.content:
        for block in result.content:
            if getattr(block, "type", None) != "resource_link":
                continue
            name = getattr(block, "name", "") or ""
            uri = getattr(block, "uri", None)
            if uri is None:
                continue
            if f"({grid_index})" in name or (grid_index == 0 and "Full resolution" in name):
                return str(uri)
    return None


def extract_cdn_url(result: Any, grid_index: int = 0) -> str | None:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        images = structured.get("images")
        if isinstance(images, list) and images:
            idx = min(grid_index, len(images) - 1)
            entry = images[idx]
            if isinstance(entry, dict) and entry.get("cdn_url"):
                return str(entry["cdn_url"])
    return None


def _is_grid_result(result: Any) -> bool:
    """Midjourney returns a 4-up contact sheet unless we fetch a single cell."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        images = structured.get("images")
        if isinstance(images, list) and len(images) > 1:
            return True
    data = getattr(result, "data", None)
    if data is not None and hasattr(data, "images") and len(data.images) > 1:
        return True
    return False


def _decode_resource_blob(blob: Any) -> bytes | None:
    if blob is None:
        return None
    if isinstance(blob, bytes):
        return blob
    if isinstance(blob, str):
        try:
            return base64.b64decode(blob)
        except Exception:
            return None
    return None


async def _read_resource_image(client: Client, uri: str) -> tuple[bytes, str] | None:
    try:
        contents = await client.read_resource(uri)
    except Exception as exc:
        logger.warning("Midjourney read_resource failed for %s: %s", uri, exc)
        return None
    for item in contents or []:
        data = _decode_resource_blob(getattr(item, "blob", None))
        if not data:
            continue
        mime = getattr(item, "mimeType", None) or getattr(item, "mime_type", None) or "image/jpeg"
        return data, str(mime)
    return None


async def _save_result_image(
    result: Any,
    dest: Path,
    *,
    client: Client | None = None,
    grid_index: int = 0,
    auth: httpx.Auth | str | None = None,
) -> Path | None:
    """Persist a single full-resolution image (never the 4-up grid preview)."""
    grid_result = _is_grid_result(result)

    if client is not None:
        uri = extract_resource_uri(result, grid_index=grid_index)
        if uri:
            payload = await _read_resource_image(client, uri)
            if payload is not None:
                data, mime = payload
                saved = _write_image_bytes(data, mime, dest)
                logger.info("Midjourney saved full-res via resource %s -> %s", uri, saved.name)
                return saved
            logger.warning("Midjourney resource %s returned no image bytes", uri)

    cdn_url = extract_cdn_url(result, grid_index=grid_index)
    if cdn_url:
        try:
            return await _download_image(cdn_url, dest, auth=auth)
        except Exception as exc:
            logger.warning("Midjourney CDN cell download failed for %s: %s", cdn_url, exc)

    if grid_result:
        logger.warning("Midjourney grid result for %s — skipping inline preview (4-up contact sheet)", dest.stem)
        return None

    inline = extract_inline_image(result)
    if inline is not None:
        data, mime = inline
        return _write_image_bytes(data, mime, dest)
    return None


async def _resolve_imagine_tool(client: Client) -> str:
    tools = await client.list_tools()
    names = {tool.name for tool in tools}
    for candidate in IMAGINE_TOOL_CANDIDATES:
        if candidate in names:
            return candidate
    for tool in tools:
        if "imagine" in tool.name.lower():
            return tool.name
    raise RuntimeError(f"No imagine tool found. Available: {sorted(names)}")


def _prompt_with_aspect(prompt: str, aspect_ratio: str) -> str:
    if "--ar" in prompt:
        return prompt
    return f"{prompt} --ar {aspect_ratio}"


async def _download_image(url: str, dest: Path, auth: httpx.Auth | str | None = None) -> Path:
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0, auth=auth) as client:
        response = await client.get(url)
        response.raise_for_status()
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            content_type = response.headers.get("content-type", "")
            if "png" in content_type:
                suffix = ".png"
            elif "jpeg" in content_type or "jpg" in content_type:
                suffix = ".jpg"
            elif "webp" in content_type:
                suffix = ".webp"
            else:
                suffix = ".png"
        final_path = dest if dest.suffix == suffix else dest.with_suffix(suffix)
        final_path.write_bytes(response.content)
        return final_path


async def generate_invite_assets_via_mcp(
    *,
    briefs: list[tuple[str, str, str]],
    asset_dir: Path,
    settings: Settings | None = None,
) -> list[str] | None:
    """Generate separate invite-quality images — one MCP call per asset, one grid cell each."""
    cfg = settings or get_settings()
    auth = _client_auth(cfg)
    if not cfg.midjourney_mcp_enabled or auth is None:
        return None

    timeout = float(cfg.midjourney_mcp_timeout_seconds)
    url = cfg.midjourney_mcp_url.rstrip("/")

    try:
        async with Client(url, auth=auth, timeout=timeout) as client:
            tool_name = await _resolve_imagine_tool(client)
            paths: list[str] = []
            for filename, prompt, aspect in briefs:
                result = await client.call_tool(
                    tool_name,
                    {"prompt": _prompt_with_aspect(prompt, aspect)},
                    timeout=timeout,
                    raise_on_error=False,
                )
                saved = await _save_result_image(
                    result,
                    asset_dir / f"{filename}.png",
                    client=client,
                    grid_index=0,
                    auth=auth,
                )
                if saved:
                    paths.append(str(saved))
                    logger.info("Midjourney saved %s", saved.name)
                else:
                    logger.warning("Midjourney returned no saveable image for %s", filename)

            if not paths:
                logger.warning("Midjourney MCP returned no invite assets")
                return None
            return paths
    except Exception as exc:
        logger.warning("Midjourney MCP generation failed: %s", exc)
        return None


async def generate_images_via_mcp(
    *,
    logo_prompt: str,
    hero_prompt: str,
    asset_dir: Path,
    settings: Settings | None = None,
) -> list[str] | None:
    """Legacy logo + hero entry point — delegates to invite asset generation."""
    briefs = [
        ("invite_motif", logo_prompt, "1:1"),
        ("invite_hero", hero_prompt, "16:9"),
    ]
    return await generate_invite_assets_via_mcp(
        briefs=briefs,
        asset_dir=asset_dir,
        settings=settings,
    )
