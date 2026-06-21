import httpx
import pytest

from app.config import Settings
from app.integrations.supabase import SupabaseRegistrationStore


@pytest.mark.asyncio
async def test_save_registration_posts_to_supabase(monkeypatch):
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    async def fake_post(self, url, *, headers, json):
        calls.append({"url": url, "headers": headers, "json": json})
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    store = SupabaseRegistrationStore(
        Settings(
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="service-key",
        )
    )
    ok = await store.save_registration(
        site_slug="phone_15551234567",
        event_name="Demo Hack",
        form_data={"name": "Ada", "email": "ada@example.com"},
        registered_at="2026-06-21T00:00:00+00:00",
    )

    assert ok is True
    assert len(calls) == 1
    assert calls[0]["url"] == "https://example.supabase.co/rest/v1/registrations"
    assert calls[0]["json"]["site_slug"] == "phone_15551234567"
    assert calls[0]["json"]["name"] == "Ada"


@pytest.mark.asyncio
async def test_save_registration_noop_when_unconfigured():
    store = SupabaseRegistrationStore(Settings(supabase_url="", supabase_service_role_key=""))
    ok = await store.save_registration(
        site_slug="x",
        event_name="x",
        form_data={},
        registered_at="2026-06-21T00:00:00+00:00",
    )
    assert ok is False
