import httpx
import pytest

from app.config import get_settings
from app.integrations import image_prompt_smith as smith
from app.integrations.midjourney import InviteAssetBrief
from app.memory.schema import EventProfile


def _profile() -> EventProfile:
    p = EventProfile(session_id="phone:test")
    p.event.name = "AI Hackathon Berkeley"
    p.aesthetic.colors = ["blue", "yellow"]
    p.aesthetic.theme = "Academic, Tech"
    return p


def _briefs() -> list[InviteAssetBrief]:
    return [
        InviteAssetBrief("invite_cover", "Invite cover", "3:4", "photo cover"),
        InviteAssetBrief("invite_hero", "Event atmosphere", "16:9", "cinematic photo"),
    ]


def test_parse_prompt_map_from_fenced_json():
    out = smith._parse_prompt_map('```json\n{"invite_cover": "flat icon"}\n```')
    assert out == {"invite_cover": "flat icon"}


def test_parse_prompt_map_handles_garbage():
    assert smith._parse_prompt_map("not json at all") == {}


def test_load_guidelines_strips_frontmatter():
    g = smith._load_guidelines()
    assert not g.startswith("---")
    assert "clip art" in g.lower()


@pytest.mark.asyncio
async def test_craft_disabled_returns_original(monkeypatch):
    monkeypatch.setenv("IMAGE_PROMPT_SMITH_ENABLED", "false")
    get_settings.cache_clear()
    briefs = _briefs()
    out = await smith.craft_invite_prompts(_profile(), briefs, get_settings())
    assert out is briefs
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_craft_no_api_key_returns_original(monkeypatch):
    monkeypatch.setenv("IMAGE_PROMPT_SMITH_ENABLED", "true")
    monkeypatch.setattr(smith, "resolve_openrouter_api_key", lambda cfg: "")
    get_settings.cache_clear()
    briefs = _briefs()
    out = await smith.craft_invite_prompts(_profile(), briefs, get_settings())
    assert out == briefs
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_craft_rewrites_scenes(monkeypatch):
    monkeypatch.setenv("IMAGE_PROMPT_SMITH_ENABLED", "true")
    monkeypatch.setattr(smith, "resolve_openrouter_api_key", lambda cfg: "sk-test")
    get_settings.cache_clear()

    payload = {
        "choices": [
            {
                "message": {
                    "content": '{"invite_cover": "flat vector clip art cover", '
                    '"invite_hero": "minimal flat banner"}'
                }
            }
        ]
    }

    class _Resp:
        status_code = 200

        def json(self):
            return payload

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    out = await smith.craft_invite_prompts(_profile(), _briefs(), get_settings())
    by_name = {b.filename: b.scene for b in out}
    assert by_name["invite_cover"] == "flat vector clip art cover"
    assert by_name["invite_hero"] == "minimal flat banner"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_craft_http_error_returns_original(monkeypatch):
    monkeypatch.setenv("IMAGE_PROMPT_SMITH_ENABLED", "true")
    monkeypatch.setattr(smith, "resolve_openrouter_api_key", lambda cfg: "sk-test")
    get_settings.cache_clear()

    class _Resp:
        status_code = 500
        text = "boom"

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    briefs = _briefs()
    out = await smith.craft_invite_prompts(_profile(), briefs, get_settings())
    assert out == briefs
    get_settings.cache_clear()
