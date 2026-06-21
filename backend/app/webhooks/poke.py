from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.integrations.poke import verify_poke_signature
from app.orchestrator.sai import get_dispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/poke", tags=["poke"])


class PokeInboundMessage(BaseModel):
    from_number: str = Field(alias="from")
    body: str
    message_id: str | None = None

    model_config = {"populate_by_name": True}


class PokeWebhookResponse(BaseModel):
    ok: bool
    replies: list[str] = Field(default_factory=list)


@router.post("", response_model=PokeWebhookResponse)
async def poke_webhook(
    request: Request,
    x_poke_signature: str | None = Header(default=None, alias="X-Poke-Signature"),
) -> PokeWebhookResponse:
    settings = get_settings()
    raw_body = await request.body()
    payload = PokeInboundMessage.model_validate_json(raw_body)

    if settings.app_env != "development":
        if not verify_poke_signature(raw_body, x_poke_signature, settings.poke_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    logger.info("poke inbound from=%s body=%r", payload.from_number, payload.body[:80])
    dispatcher = get_dispatcher()
    result = await dispatcher.dispatch(payload.from_number, payload.body)
    return PokeWebhookResponse(ok=True, replies=result.replies)
