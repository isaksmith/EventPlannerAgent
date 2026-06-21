import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.config import get_settings
from app.integrations.browserbase import provision_platforms
from app.integrations.claude_code import build_and_deploy_site, _build_site_html
from app.integrations.midjourney import build_design_seed, build_invite_asset_briefs, generate_brand_assets
from app.integrations.outreach import compile_outreach_drafts
from app.integrations.token_compression import compress_profile_context
from app.memory.schema import EventProfile, EventType, SessionStatus
from app.orchestrator.executor import format_handoff_message, run_execution


@pytest.fixture
def hackathon_profile() -> EventProfile:
    profile = EventProfile.new_session("+15551234567")
    profile.event.name = "Berkeley AI Hackathon"
    profile.event.type = EventType.HACKATHON
    profile.event.dates = "March 2026"
    profile.event.location = "Berkeley, CA"
    profile.event.expected_attendees = 200
    profile.aesthetic.vibe = "futuristic blue"
    profile.aesthetic.colors = ["#2563eb"]
    profile.ops.needs_slack = True
    profile.ops.needs_devpost = True
    profile.outreach.sponsor_targets = ["Anthropic"]
    profile.approvals.plan_approved = True
    profile.status = SessionStatus.EXECUTING
    return profile


@pytest.mark.asyncio
async def test_compress_profile_context_truncates():
    profile = EventProfile.new_session("+1")
    profile.audience.description = "x" * 500
    text = compress_profile_context(profile, max_chars=200)
    assert len(text) <= 200


def test_build_design_seed_includes_style_suffix(hackathon_profile):
    seed = build_design_seed(hackathon_profile)
    assert "--style raw" in seed
    assert "Marquee" in seed


def test_build_invite_asset_briefs_party():
    profile = EventProfile.new_session("+1")
    profile.event.name = "Summer Soirée"
    profile.event.type = EventType.PARTY
    profile.event.dates = "August 12"
    profile.event.location = "Rooftop, Brooklyn"
    profile.aesthetic.vibe = "warm and playful"
    profile.aesthetic.theme = "tropical sunset"
    profile.aesthetic.colors = ["gold", "pink"]
    profile.audience.description = "friends and coworkers"

    briefs = build_invite_asset_briefs(profile)
    assert len(briefs) == 4
    assert briefs[0].filename == "invite_cover"
    joined = " ".join(b.scene for b in briefs).lower()
    assert "tropical sunset" in joined
    assert "not a grid" in joined
    assert "summer soirée" in joined or "summer soir" in joined


def test_build_invite_asset_briefs_hackathon():
    profile = EventProfile.new_session("+1")
    profile.event.name = "Berkeley AI Hackathon"
    profile.event.type = EventType.HACKATHON
    profile.aesthetic.theme = "neon cyberpunk"
    briefs = build_invite_asset_briefs(profile)
    assert "poster key art" in briefs[0].scene.lower() or "poster" in briefs[0].scene.lower()


@pytest.mark.asyncio
async def test_generate_brand_assets_openrouter_primary(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_IMAGE_PRIMARY", "true")
    from app.config import get_settings

    get_settings.cache_clear()

    mcp = AsyncMock(return_value=["should-not-run"])
    or_mock = AsyncMock(return_value=[str(tmp_path / "assets" / "x" / "invite_cover.png")])

    with patch("app.integrations.midjourney.generate_invite_assets_via_mcp", new=mcp):
        with patch("app.integrations.midjourney.generate_invite_assets_via_openrouter", new=or_mock):
            profile = await generate_brand_assets(hackathon_profile)

    or_mock.assert_awaited_once()
    mcp.assert_not_awaited()
    assert profile.artifacts.asset_urls


@pytest.mark.asyncio
async def test_generate_brand_assets_openrouter_fallback(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("MIDJOURNEY_MCP_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    from app.config import get_settings

    get_settings.cache_clear()

    with patch(
        "app.integrations.midjourney.generate_invite_assets_via_openrouter",
        new=AsyncMock(return_value=[str(tmp_path / "assets" / "x" / "invite_cover.png")]),
    ):
        profile = await generate_brand_assets(hackathon_profile)
    assert profile.artifacts.asset_urls


@pytest.mark.asyncio
async def test_generate_brand_assets_writes_files(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("MIDJOURNEY_MCP_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_IMAGE_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()

    profile = await generate_brand_assets(hackathon_profile)
    assert profile.artifacts.asset_urls
    assert profile.artifacts.asset_dir
    assert Path(profile.artifacts.asset_dir).exists()


def test_build_site_html_contains_event_name(hackathon_profile):
    html = _build_site_html(hackathon_profile, slug="phone_15551234567")
    assert "Berkeley AI Hackathon" in html
    assert "Bebas Neue" in html
    assert './register' in html


@pytest.mark.asyncio
async def test_build_and_deploy_site_public_url(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.ngrok-free.dev")
    monkeypatch.setenv("OPENCODE_ENABLED", "false")
    monkeypatch.setenv("SITE_CODER_ENABLED", "false")
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()

    # Simulate Vercel unavailable so we exercise the self-hosted public_base_url fallback.
    async def _no_vercel(*args, **kwargs):
        return None

    monkeypatch.setattr("app.integrations.claude_code.deploy_site_to_vercel", _no_vercel)

    hackathon_profile = await generate_brand_assets(hackathon_profile)
    profile = await build_and_deploy_site(hackathon_profile)
    assert profile.artifacts.site_url.startswith("https://demo.ngrok-free.dev/sites/")


def test_outreach_drafts_are_tier3(hackathon_profile):
    hackathon_profile.artifacts.site_url = "https://example.com"
    drafts = compile_outreach_drafts(hackathon_profile)
    assert drafts
    assert any("DRAFT" in d for d in drafts)
    assert any("Anthropic" in d for d in drafts)


@pytest.mark.asyncio
async def test_browserbase_graceful_without_api_key(hackathon_profile, monkeypatch):
    monkeypatch.setenv("SLACK_ACCESS_TOKEN", "")
    monkeypatch.setenv("DEVPOST_ENABLED", "false")
    get_settings.cache_clear()

    result = await provision_platforms(hackathon_profile)
    assert result.success is False
    assert not hackathon_profile.artifacts.slack_url
    assert not hackathon_profile.artifacts.devpost_url
    assert hackathon_profile.artifacts.fallback_guides


@pytest.mark.asyncio
async def test_run_execution_full_pipeline(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("BROWSERBASE_ENABLED", "false")
    monkeypatch.setenv("OPENCODE_ENABLED", "false")
    monkeypatch.setenv("SITE_CODER_ENABLED", "false")
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "false")
    monkeypatch.setenv("SITE_CODER_ENABLED", "false")
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_IMAGE_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()

    progress: list[str] = []

    async def on_progress(msg: str) -> None:
        progress.append(msg)

    profile = await run_execution(hackathon_profile, on_progress=on_progress)
    assert profile.status == SessionStatus.AWAITING_HANDOFF
    assert profile.artifacts.site_url
    assert profile.artifacts.outreach_drafts
    assert progress


def test_format_handoff_message(hackathon_profile):
    hackathon_profile.artifacts.site_url = "https://demo.vercel.app"
    hackathon_profile.artifacts.outreach_drafts = ["draft1"]
    msg = format_handoff_message(hackathon_profile)
    assert "SEND" in msg
    assert "demo.vercel.app" in msg
