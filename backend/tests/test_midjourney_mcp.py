from types import SimpleNamespace

import pytest

from app.integrations.midjourney_mcp import (
    extract_image_urls,
    extract_inline_image,
    extract_resource_uri,
    mcp_configured,
    _is_grid_result,
    _write_image_bytes,
)
from app.config import Settings


def test_extract_inline_image_from_mcp_block():
    payload = b"fake-image-bytes"
    import base64

    result = SimpleNamespace(
        content=[
            SimpleNamespace(type="image", data=base64.b64encode(payload).decode(), mimeType="image/webp"),
        ],
    )
    decoded = extract_inline_image(result)
    assert decoded is not None
    data, mime = decoded
    assert data == payload
    assert mime == "image/webp"


def test_write_image_bytes_uses_mime_suffix(tmp_path):
    path = _write_image_bytes(b"x", "image/webp", tmp_path / "logo.png")
    assert path.name == "logo.webp"
    assert path.read_bytes() == b"x"


def test_is_grid_result_detects_four_up():
    result = SimpleNamespace(
        structured_content={
            "images": [
                {"grid_index": 0, "resource_uri": "midjourney://image/job/0"},
                {"grid_index": 1, "resource_uri": "midjourney://image/job/1"},
            ]
        },
        content=[],
    )
    assert _is_grid_result(result) is True


def test_extract_resource_uri_from_structured():
    result = SimpleNamespace(
        structured_content={
            "images": [
                {"grid_index": 0, "resource_uri": "midjourney://image/job/0"},
                {"grid_index": 1, "resource_uri": "midjourney://image/job/1"},
            ]
        },
        content=[],
    )
    assert extract_resource_uri(result, 0) == "midjourney://image/job/0"
    assert extract_resource_uri(result, 1) == "midjourney://image/job/1"


def test_extract_image_urls_from_text():
    result = SimpleNamespace(
        structured_content=None,
        data=None,
        content=[SimpleNamespace(text="See https://cdn.example.com/out.png for result")],
    )
    assert extract_image_urls(result) == ["https://cdn.example.com/out.png"]


def test_extract_image_urls_from_structured():
    result = SimpleNamespace(
        structured_content={"image_url": "https://cdn.example.com/hero.jpg"},
        data=None,
        content=[],
    )
    assert extract_image_urls(result) == ["https://cdn.example.com/hero.jpg"]


def test_mcp_configured_requires_enabled_and_auth():
    assert not mcp_configured(Settings(midjourney_mcp_enabled=False, midjourney_mcp_token="x"))
    assert mcp_configured(Settings(midjourney_mcp_enabled=True, midjourney_mcp_token="token"))
    assert mcp_configured(
        Settings(midjourney_mcp_enabled=True, midjourney_mcp_use_oauth=True, midjourney_mcp_token="")
    )
