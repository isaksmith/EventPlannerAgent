"""Image prompt smith — DeepSeek rewrites brand-asset briefs into clean,
minimalistic 2D clip-art image-generation prompts themed to the specific event.

Runs *before* the briefs are sent to the image generation API. On any failure
(disabled, missing key, bad response, timeout) it returns the original briefs
unchanged so brand generation never regresses.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from app.config import Settings, get_settings
from app.integrations.openrouter_auth import resolve_openrouter_api_key
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

if TYPE_CHECKING:
    from app.integrations.midjourney import InviteAssetBrief

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SKILL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "skills"
    / "image-prompt-smith"
    / "SKILL.md"
)

_FALLBACK_GUIDELINES = (
    "You are an art director. Rewrite each event asset brief into ONE precise prompt "
    "for a minimalistic, clean, modern 2D flat vector clip-art illustration themed to "
    "the event. One clear subject, generous negative space, cohesive limited palette "
    "from the event's brand colors. Avoid AI-slop clip art: no clutter, no 3D, no "
    "photorealism, no gradient-mesh blobs, no drop shadows, no text/letters/logos in "
    "the image. Return only a JSON object mapping each filename to its prompt."
)


def _load_guidelines() -> str:
    try:
        text = _SKILL_PATH.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK_GUIDELINES
    # Strip the YAML frontmatter so only the instruction body is sent.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()


def _headers(cfg: Settings, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if cfg.openrouter_site_url:
        headers["HTTP-Referer"] = cfg.openrouter_site_url
    if cfg.openrouter_app_name:
        headers["X-Title"] = cfg.openrouter_app_name
    return headers


def _event_context(profile: EventProfile) -> str:
    e = profile.event
    a = profile.aesthetic
    colors = ", ".join(a.colors) or "(choose a tasteful cohesive palette)"
    theme = a.theme or a.vibe or "clean and modern"
    audience = profile.audience.description or "general audience"
    return (
        f"Event name: {e.name or 'Untitled event'}\n"
        f"Event type: {e.type_label or e.type.value}\n"
        f"Theme: {theme}\n"
        f"Vibe: {a.vibe or theme}\n"
        f"Brand colors: {colors}\n"
        f"Audience: {audience}\n"
        f"Location: {e.location or 'TBD'}"
    )


def _parse_prompt_map(content: str) -> dict[str, str]:
    """Extract the JSON {filename: prompt} object from a model response."""
    if not content:
        return {}
    candidate = content.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    else:
        brace = candidate.find("{")
        end = candidate.rfind("}")
        if brace != -1 and end != -1 and end > brace:
            candidate = candidate[brace : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v.strip()}


async def craft_invite_prompts(
    profile: EventProfile,
    briefs: list["InviteAssetBrief"],
    settings: Settings | None = None,
) -> list["InviteAssetBrief"]:
    """Rewrite brief scenes into clean 2D clip-art prompts via DeepSeek.

    Returns a new list of briefs with refined ``scene`` text, or the original
    briefs unchanged on any failure.
    """
    from app.integrations.midjourney import InviteAssetBrief

    cfg = settings or get_settings()
    if not cfg.image_prompt_smith_enabled or not briefs:
        return briefs

    api_key = resolve_openrouter_api_key(cfg)
    if not api_key:
        logger.info("Image prompt smith skipped — no OpenRouter API key")
        return briefs

    model = cfg.image_prompt_model or cfg.openrouter_model
    asset_lines = "\n".join(
        f"- {b.filename} (aspect {b.aspect}, purpose: {b.label}): {b.scene}"
        for b in briefs
    )
    user_prompt = (
        f"Event context:\n{_event_context(profile)}\n\n"
        f"Rewrite the prompt for each of these {len(briefs)} brand assets as clean, "
        "minimalistic 2D clip-art image-generation prompts themed to this event. "
        "Keep the same filenames and respect each asset's aspect ratio and purpose.\n\n"
        f"Assets:\n{asset_lines}\n\n"
        'Return only JSON: {"invite_cover": "…", "invite_hero": "…", ...}'
    )
    messages = [
        {"role": "system", "content": _load_guidelines()},
        {"role": "user", "content": user_prompt},
    ]

    tracer = get_tracer()
    try:
        async with tracer.span(
            "image_prompt_smith.craft",
            session_id=profile.session_id,
            model=model,
            count=len(briefs),
        ):
            async with httpx.AsyncClient(
                timeout=cfg.image_prompt_smith_timeout_seconds
            ) as client:
                response = await client.post(
                    OPENROUTER_URL,
                    headers=_headers(cfg, api_key),
                    json={
                        "model": model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                    },
                )
        if response.status_code >= 400:
            logger.warning(
                "Image prompt smith HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )
            return briefs
        content = response.json()["choices"][0]["message"].get("content") or ""
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.warning("Image prompt smith failed (%s); using base briefs", exc)
        return briefs

    prompt_map = _parse_prompt_map(content)
    if not prompt_map:
        logger.warning("Image prompt smith returned no usable prompts; using base briefs")
        return briefs

    refined: list[InviteAssetBrief] = []
    used = 0
    for b in briefs:
        new_scene = prompt_map.get(b.filename)
        if new_scene:
            used += 1
            refined.append(InviteAssetBrief(b.filename, b.label, b.aspect, new_scene))
        else:
            refined.append(b)
    logger.info("Image prompt smith refined %d/%d asset prompts via %s", used, len(briefs), model)
    return refined
