from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class SupabaseRegistrationStore:
    """Persist registration form submissions via Supabase PostgREST."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self._settings.supabase_url and self._settings.supabase_service_role_key)

    def _headers(self) -> dict[str, str]:
        key = self._settings.supabase_service_role_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    async def save_registration(
        self,
        *,
        site_slug: str,
        event_name: str,
        form_data: dict[str, Any],
        registered_at: str,
    ) -> bool:
        if not self.enabled:
            return False

        row = {
            "site_slug": site_slug,
            "event_name": event_name,
            "name": form_data.get("name"),
            "email": form_data.get("email"),
            "form_data": form_data,
            "registered_at": registered_at,
        }
        url = f"{self._settings.supabase_url.rstrip('/')}/rest/v1/registrations"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=self._headers(), json=row)
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Supabase registration insert failed: %s", exc)
            return False


def get_registration_store(settings: Settings | None = None) -> SupabaseRegistrationStore:
    return SupabaseRegistrationStore(settings)
