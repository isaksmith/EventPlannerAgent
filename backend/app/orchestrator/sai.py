from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.integrations.poke import send_sms
from app.memory.redis_store import SessionStore, get_session_store
from app.memory.schema import EventProfile, SessionStatus
from app.observability.arize import get_tracer
from app.orchestrator.approval_gate import handle_approval_gate
from app.orchestrator.executor import format_final_delivery, format_handoff_message, run_execution
from app.orchestrator.state_machine import advance_interview, compile_summary, start_interview

logger = logging.getLogger(__name__)

PLAN_KEYWORD = "PLAN"
WELCOME_TEXT = (
    "Welcome to Marquee! I'll ask a few questions, then show you a plan to approve."
)


@dataclass
class DispatchResult:
    replies: list[str]
    profile: EventProfile | None = None


class SaiDispatcher:
    """Simular Sai dispatcher — routes inbound SMS to phase handlers."""

    def __init__(self, store: SessionStore | None = None) -> None:
        self._store = store or get_session_store()
        self._tracer = get_tracer()
        self._execution_tasks: dict[str, asyncio.Task[None]] = {}

    async def dispatch(self, phone: str, message: str, *, deliver_sms: bool = True) -> DispatchResult:
        text = message.strip()
        async with self._tracer.span("sai.dispatch", phone=phone, message_len=len(text)):
            profile = await self._store.get(phone)

            if profile is None:
                if text.upper() == PLAN_KEYWORD:
                    return await self._init_session(phone, deliver_sms=deliver_sms)
                return DispatchResult(
                    replies=[f"Text {PLAN_KEYWORD} to start planning your event."],
                )

            if profile.status == SessionStatus.INTERVIEWING:
                return await self._handle_interview(profile, text, deliver_sms=deliver_sms)

            if profile.status == SessionStatus.AWAITING_APPROVAL:
                return await self._handle_approval(profile, text, deliver_sms=deliver_sms)

            if profile.status == SessionStatus.EXECUTING:
                return DispatchResult(
                    replies=["Build in progress — I'll text you when there's an update."],
                    profile=profile,
                )

            if profile.status == SessionStatus.AWAITING_HANDOFF:
                return await self._handle_handoff(profile, text, deliver_sms=deliver_sms)

            return DispatchResult(
                replies=["Session complete. Text PLAN to start a new event."],
                profile=profile,
            )

    def _phone(self, profile: EventProfile) -> str:
        return profile.session_id.removeprefix("phone:")

    async def _send_replies(self, profile: EventProfile, replies: list[str], deliver_sms: bool) -> None:
        if not deliver_sms:
            return
        for reply in replies:
            await send_sms(self._phone(profile), reply)

    async def _init_session(self, phone: str, *, deliver_sms: bool = True) -> DispatchResult:
        async with self._tracer.span("sai.init_session", phone=phone):
            profile = EventProfile.new_session(phone)
            profile, first_question = start_interview(profile)
            await self._store.save(profile)
            replies = [WELCOME_TEXT, first_question]
            await self._send_replies(profile, replies, deliver_sms)
            return DispatchResult(replies=replies, profile=profile)

    async def _handle_interview(
        self, profile: EventProfile, text: str, *, deliver_sms: bool = True
    ) -> DispatchResult:
        async with self._tracer.span(
            "sai.interview",
            step=profile.interview_step,
            session_id=profile.session_id,
        ):
            profile, next_prompt, complete = advance_interview(profile, text)
            replies: list[str] = []

            if complete:
                replies.append("Got it, building your plan…")
                summary = compile_summary(profile)
                replies.append(summary)
            elif next_prompt:
                replies.append(next_prompt)

            await self._store.save(profile)
            await self._send_replies(profile, replies, deliver_sms)
            return DispatchResult(replies=replies, profile=profile)

    async def wait_for_execution(self, session_id: str) -> None:
        """Test helper — await a background build task if one is running."""
        sid = session_id if session_id.startswith("phone:") else f"phone:{session_id}"
        task = self._execution_tasks.get(sid)
        if task:
            await task

    async def _run_execution_background(
        self,
        profile: EventProfile,
        *,
        deliver_sms: bool,
    ) -> None:
        session_id = profile.session_id

        async def on_progress(msg: str) -> None:
            if deliver_sms:
                await send_sms(self._phone(profile), msg)

        async def on_checkpoint(p: EventProfile) -> None:
            await self._store.save(p)

        try:
            profile = await run_execution(
                profile,
                on_progress=on_progress,
                on_checkpoint=on_checkpoint,
            )
            await self._store.save(profile)
            handoff = format_handoff_message(profile)
            if deliver_sms:
                await send_sms(self._phone(profile), handoff)
        except Exception:
            logger.exception("Background execution failed for %s", session_id)
            failed = await self._store.get(session_id)
            if failed is not None:
                failed.status = SessionStatus.AWAITING_HANDOFF
                await self._store.save(failed)
        finally:
            self._execution_tasks.pop(session_id, None)

    async def _handle_approval(
        self, profile: EventProfile, text: str, *, deliver_sms: bool = True
    ) -> DispatchResult:
        async with self._tracer.span("sai.approval_gate", session_id=profile.session_id):
            profile, reply, approved = handle_approval_gate(profile, text)
            await self._store.save(profile)
            if deliver_sms:
                await send_sms(self._phone(profile), reply)

            if not approved:
                return DispatchResult(replies=[reply], profile=profile)

            build_reply = (
                "On it! I'll build everything now and show you each piece as it's ready. Sit tight."
            )
            self._execution_tasks[profile.session_id] = asyncio.create_task(
                self._run_execution_background(profile, deliver_sms=deliver_sms)
            )
            return DispatchResult(replies=[reply, build_reply], profile=profile)

    async def _handle_handoff(
        self, profile: EventProfile, text: str, *, deliver_sms: bool = True
    ) -> DispatchResult:
        """Phase 4 — Tier-3 per-action approval gate."""
        async with self._tracer.span("sai.handoff_gate", session_id=profile.session_id):
            normalized = text.strip().upper()

            if normalized in {"ALL-SKIP", "SKIP ALL", "DONE", "FINISH"}:
                profile.status = SessionStatus.DONE
                delivery = format_final_delivery(profile)
                profile.approvals.handoff_decisions.append({"action": "all_skip"})
                await self._store.save(profile)
                if deliver_sms:
                    await send_sms(self._phone(profile), delivery)
                return DispatchResult(replies=[delivery], profile=profile)

            if normalized.startswith("SKIP"):
                profile.approvals.handoff_decisions.append({"action": "skip", "detail": text})
                reply = "Skipped. Reply SEND for next draft, or ALL-SKIP to finish."
                await self._store.save(profile)
                if deliver_sms:
                    await send_sms(self._phone(profile), reply)
                return DispatchResult(replies=[reply], profile=profile)

            if normalized.startswith("SEND"):
                profile.approvals.handoff_decisions.append({"action": "send_queued", "detail": text})
                reply = (
                    "Send queued for human review (Tier 3 — not auto-sent in demo). "
                    "Reply ALL-SKIP when done."
                )
                await self._store.save(profile)
                if deliver_sms:
                    await send_sms(self._phone(profile), reply)
                return DispatchResult(replies=[reply], profile=profile)

            if normalized.startswith("EDIT"):
                profile.approvals.handoff_decisions.append({"action": "edit", "detail": text})
                reply = "Noted — revise drafts manually. Reply ALL-SKIP to finish."
                await self._store.save(profile)
                if deliver_sms:
                    await send_sms(self._phone(profile), reply)
                return DispatchResult(replies=[reply], profile=profile)

            handoff = format_handoff_message(profile)
            reply = f"Reply SEND, EDIT, SKIP, or ALL-SKIP.\n\n{handoff}"
            if deliver_sms:
                await send_sms(self._phone(profile), reply)
            return DispatchResult(replies=[reply], profile=profile)


_dispatcher: SaiDispatcher | None = None


def get_dispatcher(store: SessionStore | None = None) -> SaiDispatcher:
    global _dispatcher
    if _dispatcher is None or store is not None:
        _dispatcher = SaiDispatcher(store)
    return _dispatcher
