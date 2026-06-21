from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _resolve_dir(path: str) -> str:
    p = Path(path)
    return str(p if p.is_absolute() else _BACKEND_ROOT / p)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    poke_webhook_secret: str = "dev-secret"
    poke_api_base_url: str = "https://api.poke.dev/v1"
    poke_api_key: str = ""

    arize_enabled: bool = False
    arize_api_key: str = ""
    arize_space_id: str = ""
    arize_project_name: str = "orchestrateai"

    app_env: str = "development"
    log_level: str = "info"

    assets_output_dir: str = "var/assets"
    build_output_dir: str = "var/builds"
    archive_output_dir: str = "var/archive"  # completed-event snapshots for Past Events
    public_base_url: str = ""  # e.g. https://your-subdomain.ngrok-free.dev

    vercel_token: str = ""
    vercel_team_id: str = ""

    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    browserbase_enabled: bool = True
    browserbase_verify_site: bool = True
    browserbase_test_registration: bool = True
    browserbase_verify_slack: bool = True

    slack_access_token: str = ""
    slack_refresh_token: str = ""
    slack_invite_url: str = ""  # optional join link; falls back to workspace URL

    devpost_enabled: bool = False

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""
    supabase_db_password: str = ""

    midjourney_api_key: str = ""  # legacy; prefer Midjourney MCP below

    midjourney_mcp_enabled: bool = False
    midjourney_mcp_url: str = "https://mcp.midjourney.com/mcp"
    midjourney_mcp_token: str = ""
    midjourney_mcp_use_oauth: bool = False
    midjourney_mcp_timeout_seconds: int = 480

    pika_enabled: bool = False
    pika_api_key: str = ""  # fal.ai API key (Pika models hosted on fal)
    pika_model_text: str = "fal-ai/pika/v2.2/text-to-video"
    pika_model_image: str = "fal-ai/pika/v2.2/image-to-video"
    pika_duration_seconds: int = 5
    pika_resolution: str = "720p"
    pika_aspect_ratio: str = "16:9"
    pika_use_hero_image: bool = True
    pika_timeout_seconds: int = 300

    # OpenRouter site coder — UI/UX Pro Max + OpenRouter (primary site generation)
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-v4-flash"
    openrouter_max_turns: int = 12
    openrouter_timeout_seconds: int = 180
    openrouter_site_url: str = "https://github.com/EventPlannerAgent/marquee"
    openrouter_app_name: str = "Marquee Site Coder"
    site_coder_enabled: bool = True
    ui_ux_pro_max_enabled: bool = True
    ui_ux_pro_max_timeout_seconds: int = 30

    # OpenRouter image generation
    openrouter_image_enabled: bool = True
    openrouter_image_model: str = "openai/gpt-5.4-image-2"
    openrouter_image_timeout_seconds: int = 120
    openrouter_image_primary: bool = True  # OpenRouter first; Midjourney MCP is fallback

    # Image prompt smith — rewrites brand-asset briefs into clean 2D clip-art prompts
    # before they hit the image API. Falls back to the base briefs on any failure.
    image_prompt_smith_enabled: bool = True
    image_prompt_model: str = ""  # defaults to openrouter_model when empty
    image_prompt_smith_timeout_seconds: int = 60

    # OpenCode CLI — optional fallback site generation
    opencode_enabled: bool = False
    opencode_bin: str = "opencode"
    opencode_model: str = "openrouter/anthropic/claude-sonnet-4"
    opencode_agent: str = "site-builder"
    opencode_timeout_seconds: int = 600

    @model_validator(mode="after")
    def _absolute_data_dirs(self) -> "Settings":
        self.assets_output_dir = _resolve_dir(self.assets_output_dir)
        self.build_output_dir = _resolve_dir(self.build_output_dir)
        self.archive_output_dir = _resolve_dir(self.archive_output_dir)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
