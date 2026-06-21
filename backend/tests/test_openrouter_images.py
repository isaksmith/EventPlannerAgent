import base64

import pytest
from unittest.mock import AsyncMock, patch

from app.config import Settings, get_settings
from app.integrations.openrouter_images import (
    extract_image_data_urls,
    generate_invite_assets_via_openrouter,
    openrouter_images_configured,
    _parse_data_url,
)

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_URL = f"data:image/png;base64,{base64.b64encode(TINY_PNG).decode()}"


def test_openrouter_images_configured(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.openrouter_auth.resolve_openrouter_api_key",
        lambda _cfg=None: "",
    )
    assert not openrouter_images_configured(Settings(openrouter_api_key="", openrouter_image_enabled=True))
    monkeypatch.setattr(
        "app.integrations.openrouter_auth.resolve_openrouter_api_key",
        lambda _cfg=None: "sk-test",
    )
    assert openrouter_images_configured(
        Settings(openrouter_api_key="", openrouter_image_enabled=True)
    )


def test_parse_data_url():
    parsed = _parse_data_url(DATA_URL)
    assert parsed is not None
    data, mime = parsed
    assert mime == "image/png"
    assert data == TINY_PNG


def test_extract_image_data_urls():
    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Here is your image.",
                    "images": [{"type": "image_url", "image_url": {"url": DATA_URL}}],
                }
            }
        ]
    }
    assert extract_image_data_urls(response) == [DATA_URL]


@pytest.mark.asyncio
async def test_generate_invite_assets_via_openrouter_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_IMAGE_ENABLED", "true")
    get_settings.cache_clear()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "choices": [{"message": {"images": [{"image_url": {"url": DATA_URL}}]}}]
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    briefs = [("invite_cover", "A party invite cover", "3:4")]
    with patch("app.integrations.openrouter_images.httpx.AsyncClient", return_value=mock_client):
        paths = await generate_invite_assets_via_openrouter(briefs, tmp_path)

    assert paths
    assert (tmp_path / "invite_cover.png").is_file()
