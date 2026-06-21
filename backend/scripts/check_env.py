#!/usr/bin/env python3
"""Print the effective Settings the backend loaded (secrets masked)."""
from __future__ import annotations

from app.config import get_settings
from app.integrations.openrouter_auth import resolve_openrouter_api_key


def m(v: str | None) -> str:
    return (v[:6] + "…len" + str(len(v))) if v else "(EMPTY)"


def main() -> None:
    c = get_settings()
    print("app_env             :", c.app_env)
    print("openrouter key      :", m(resolve_openrouter_api_key(c) or ""))
    print("openrouter model    :", c.openrouter_model)
    print("image enabled/primary:", c.openrouter_image_enabled, "/", c.openrouter_image_primary)
    print("image model         :", c.openrouter_image_model)
    print("image timeout (s)   :", c.openrouter_image_timeout_seconds)
    print("prompt_smith enabled:", c.image_prompt_smith_enabled, "| timeout:", c.image_prompt_smith_timeout_seconds)
    print("site_coder/ui_ux    :", c.site_coder_enabled, "/", c.ui_ux_pro_max_enabled)
    print("openrouter_max_turns:", c.openrouter_max_turns, "| timeout:", c.openrouter_timeout_seconds)
    print("slack token         :", m(c.slack_access_token))
    print("browserbase enabled :", c.browserbase_enabled, "| key:", m(c.browserbase_api_key))
    print("vercel token        :", m(c.vercel_token))
    print("pika enabled        :", c.pika_enabled)
    print("midjourney mcp      :", c.midjourney_mcp_enabled)
    print("archive_output_dir  :", c.archive_output_dir)
    print("assets_output_dir   :", c.assets_output_dir)
    print("build_output_dir    :", c.build_output_dir)


if __name__ == "__main__":
    main()
