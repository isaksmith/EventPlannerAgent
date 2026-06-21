from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path

from app.config import Settings, get_settings
from app.integrations.site_workspace import (
    opencode_run_prompt,
    validate_generated_site,
)
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)


def opencode_available(settings: Settings) -> bool:
    if not settings.opencode_enabled:
        return False
    if shutil.which(settings.opencode_bin):
        return True
    # Common install location when not on PATH
    home_bin = Path.home() / ".opencode" / "bin" / "opencode"
    return home_bin.is_file()


def _subprocess_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    if settings.openrouter_api_key:
        env["OPENROUTER_API_KEY"] = settings.openrouter_api_key
    return env


def _resolve_opencode_bin(settings: Settings) -> str:
    if shutil.which(settings.opencode_bin):
        return settings.opencode_bin
    home_bin = Path.home() / ".opencode" / "bin" / "opencode"
    if home_bin.is_file():
        return str(home_bin)
    return settings.opencode_bin


def _build_command(build_dir: Path, settings: Settings) -> list[str]:
    cmd = [
        _resolve_opencode_bin(settings),
        "run",
        "--dir",
        str(build_dir),
        "--model",
        settings.opencode_model,
        "--agent",
        settings.opencode_agent,
        "--dangerously-skip-permissions",
        opencode_run_prompt(build_dir.name),
    ]
    return cmd


async def generate_site_with_opencode(
    build_dir: Path,
    profile: EventProfile,
    settings: Settings | None = None,
) -> tuple[bool, str]:
    """
    Run OpenCode CLI as a coding subagent in build_dir.
    Returns (success, summary_or_error).
    """
    cfg = settings or get_settings()
    if not opencode_available(cfg):
        return False, f"{cfg.opencode_bin} not found or OpenCode disabled"

    cmd = _build_command(build_dir, cfg)
    logger.info("OpenCode site build: %s", " ".join(cmd[:8]))

    tracer = get_tracer()
    async with tracer.span(
        "opencode.site_build",
        session_id=profile.session_id,
        model=cfg.opencode_model,
        agent=cfg.opencode_agent,
    ):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_subprocess_env(cfg),
            cwd=str(build_dir),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=cfg.opencode_timeout_seconds,
            )
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return False, f"OpenCode timed out after {cfg.opencode_timeout_seconds}s"

    out_tail = (stdout or b"").decode(errors="replace")[-400:]
    err_tail = (stderr or b"").decode(errors="replace")[-400:]
    if proc.returncode != 0:
        detail = err_tail or out_tail or f"exit code {proc.returncode}"
        return False, f"OpenCode failed: {detail.strip()}"

    ok, reason = validate_generated_site(build_dir / "index.html", profile)
    if ok:
        return True, "OpenCode site-builder completed"
    return False, f"OpenCode finished but validation failed: {reason}"
