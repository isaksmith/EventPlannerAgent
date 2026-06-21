from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def verify_poke_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify Poke webhook HMAC-SHA256 signature."""
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    provided = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


async def send_sms(to: str, body: str, settings: Settings | None = None) -> dict:
    """Send outbound message via Poke V2 inbound API (delivered in iMessage thread)."""
    cfg = settings or get_settings()
    if not cfg.poke_api_key:
        logger.info("[poke stub] SMS to %s: %s", to, body)
        return {"status": "stub", "to": to, "body": body}

    base = cfg.poke_api_base_url.rstrip("/")
    url = f"{base}/inbound/api-message"
    payload = {
        "message": body,
        "source": "orchestrateai",
        "metadata": {"recipient": to, "channel": "sms"},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {cfg.poke_api_key}"},
            json=payload,
            timeout=30.0,
        )
        if response.status_code >= 400:
            logger.warning("Poke api-message failed %s: %s", response.status_code, response.text[:200])
            response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"status": "sent", "raw": response.text}
