from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx
from pathvalidate import sanitize_filename

from app.config import Settings, get_settings
from app.integrations.openrouter_auth import resolve_openrouter_api_key
from app.integrations.site_workspace import validate_generated_site
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories relative to the site workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory to list (default: '.').",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from the site workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a UTF-8 text file in the site workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "Full file contents."},
                },
                "required": ["path", "content"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a senior UI/UX engineer building a single-page event registration site.

You MUST follow the UI/UX Pro Max design system provided in the user message:
- Match the recommended pattern, style, colors, and typography
- Use SVG icons (Heroicons/Lucide style inline SVG) — never emoji as icons
- Visible form labels (not placeholder-only), 44px min touch targets
- focus-visible rings, prefers-reduced-motion, 4.5:1 text contrast
- Mobile-first responsive layout (375 / 768 / 1024 / 1440)
- Single primary CTA; 150–300ms transitions on interactive elements

Workspace layout (already prepared):
- index.html — pre-rendered Marquee template (customize, do not discard registration wiring)
- UI_UX_DESIGN_SYSTEM.md — design intelligence for this event
- event_profile.json — full event data
- assets/ — brand images (invite_*.png, logo.*, hero.*)
- SITE_BRIEF.md — human-readable summary

Requirements for index.html:
1. Apply the UI/UX Pro Max design system to tailor the page to this event.
2. Keep registration: form submits via JavaScript fetch to "./register" POST with
   body = new URLSearchParams(new FormData(form)) and header
   { "Content-Type": "application/x-www-form-urlencoded" }. On success, document.write response HTML.
   (Do not change the "./register" path — deployment rewrites it to the serverless handler.)
3. Registration fields must match ops.registration_fields from the profile.
4. Reference brand assets from ./assets/ with onerror fallbacks for missing files.
5. Show event name, dates, location, expected attendees, vibe/theme prominently.
6. When the event has a physical location (event.location, not "TBD"/"virtual"/"online"), include a
   "Getting there" location section with an embedded Google Maps iframe. Use the keyless embed
   src="https://www.google.com/maps?q=<URL-encoded location>&output=embed&z=17" (strip qualifiers like
   "· in person" from the query), give the iframe a descriptive title, loading="lazy", and add a
   "Get directions" link to https://www.google.com/maps/search/?api=1&query=<URL-encoded location>.
   Skip this section for purely virtual/online events.
7. Link slack_url / devpost_url from artifacts when present.
7. Single self-contained index.html (Tailwind CDN or embedded CSS OK). Optional assets/styles.css.
8. SCROLL ANIMATIONS (required): Add scroll-triggered reveal animations using IntersectionObserver.
   - Elements (sections, cards, headings, images) should fade-in + slide-up as they enter the viewport.
   - Add CSS classes like .reveal { opacity:0; transform:translateY(30px); transition:opacity 0.6s ease, transform 0.6s ease; }
     and .reveal.visible { opacity:1; transform:translateY(0); }
   - Add a small <script> that creates an IntersectionObserver to add .visible when elements scroll into view.
   - Stagger animations with transition-delay for grouped elements (e.g., bento cards).
   - Respect prefers-reduced-motion: skip animations for users who prefer reduced motion.
9. Do not delete event_profile.json, UI_UX_DESIGN_SYSTEM.md, or files in assets/.

When finished, reply with exactly: SITE_COMPLETE
"""


def _build_system_prompt(design_system: str) -> str:
    if not design_system.strip():
        return SYSTEM_PROMPT
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "## UI/UX Pro Max Design System (REQUIRED)\n\n"
        f"{design_system.strip()}\n"
    )


def _resolve_workspace_path(build_dir: Path, rel_path: str) -> Path:
    clean = rel_path.strip().replace("\\", "/").lstrip("/")
    if clean in {"", "."}:
        return build_dir.resolve()
    parts = [sanitize_filename(p) or p for p in clean.split("/") if p not in {"", "."}]
    target = build_dir.joinpath(*parts).resolve()
    root = build_dir.resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Path escapes workspace: {rel_path}")
    return target


def _tool_list_files(build_dir: Path, rel_path: str = ".") -> str:
    target = _resolve_workspace_path(build_dir, rel_path)
    if not target.is_dir():
        return f"Not a directory: {rel_path}"
    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = []
    for entry in entries:
        kind = "dir" if entry.is_dir() else "file"
        rel = entry.relative_to(build_dir.resolve()).as_posix()
        lines.append(f"{kind}\t{rel}")
    return "\n".join(lines) or "(empty)"


def _tool_read_file(build_dir: Path, rel_path: str) -> str:
    target = _resolve_workspace_path(build_dir, rel_path)
    if not target.is_file():
        return f"File not found: {rel_path}"
    return target.read_text(encoding="utf-8")


def _tool_write_file(build_dir: Path, rel_path: str, content: str) -> str:
    target = _resolve_workspace_path(build_dir, rel_path)
    if target.is_dir():
        return f"Refusing to write over directory: {rel_path}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {rel_path}"


def _execute_tool(build_dir: Path, name: str, arguments: dict[str, Any]) -> str:
    try:
        if name == "list_files":
            return _tool_list_files(build_dir, arguments.get("path", "."))
        if name == "read_file":
            return _tool_read_file(build_dir, arguments["path"])
        if name == "write_file":
            return _tool_write_file(build_dir, arguments["path"], arguments["content"])
        return f"Unknown tool: {name}"
    except (KeyError, ValueError, OSError) as exc:
        return f"Tool error: {exc}"


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


async def generate_site_with_openrouter(
    build_dir: Path,
    profile: EventProfile,
    settings: Settings | None = None,
    *,
    design_system: str = "",
) -> tuple[bool, str]:
    """
    Primary site coder: OpenRouter tool-calling loop guided by UI/UX Pro Max design system.
    Workspace must already be prepared (template seed, SITE_BRIEF.md, event_profile.json).
    """
    cfg = settings or get_settings()
    if not resolve_openrouter_api_key(cfg):
        return False, "OPENROUTER_API_KEY not set"

    slug = build_dir.name
    ds_note = (
        "UI_UX_DESIGN_SYSTEM.md is in the workspace — read it first."
        if design_system
        else "No design system file; read SITE_BRIEF.md and event_profile.json."
    )
    user_prompt = (
        f"Customize index.html for session slug '{slug}' using the UI/UX Pro Max design system. "
        f"{ds_note} "
        "Read index.html, event_profile.json, inspect assets/, then write a polished registration landing page. "
        "When done, respond SITE_COMPLETE."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt(design_system)},
        {"role": "user", "content": user_prompt},
    ]

    tracer = get_tracer()
    async with tracer.span(
        "site_coder.openrouter",
        session_id=profile.session_id,
        model=cfg.openrouter_model,
    ):
        async with httpx.AsyncClient(timeout=cfg.openrouter_timeout_seconds) as client:
            for turn in range(1, cfg.openrouter_max_turns + 1):
                payload = {
                    "model": cfg.openrouter_model,
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto",
                }
                response = await client.post(
                    OPENROUTER_URL,
                    headers=_headers(cfg),
                    json=payload,
                )
                if response.status_code >= 400:
                    return False, f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"

                data = response.json()
                choice = data["choices"][0]
                message = choice["message"]
                messages.append(message)

                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    for call in tool_calls:
                        fn = call["function"]
                        name = fn["name"]
                        try:
                            args = json.loads(fn.get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        result = _execute_tool(build_dir, name, args)
                        logger.info(
                            "openrouter site_coder %s(%s) -> %s",
                            name,
                            args.get("path", ""),
                            result[:80],
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call["id"],
                                "content": result,
                            }
                        )
                    continue

                text = (message.get("content") or "").strip()
                if re.search(r"\bSITE_COMPLETE\b", text):
                    ok, reason = validate_generated_site(build_dir / "index.html", profile)
                    if ok:
                        return True, f"OpenRouter agent completed in {turn} turn(s)"
                    return False, f"agent finished but validation failed: {reason}"

                if choice.get("finish_reason") == "stop" and not tool_calls:
                    ok, reason = validate_generated_site(build_dir / "index.html", profile)
                    if ok:
                        return True, f"OpenRouter agent stopped after {turn} turn(s)"
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Site not valid yet ({reason}). "
                                "Fix index.html and ensure registration works, then reply SITE_COMPLETE."
                            ),
                        }
                    )

    ok, reason = validate_generated_site(build_dir / "index.html", profile)
    if ok:
        return True, "OpenRouter agent ended with valid index.html"
    return False, f"max turns exceeded; last validation: {reason}"


# Backwards-compatible alias
generate_site_with_agent = generate_site_with_openrouter
