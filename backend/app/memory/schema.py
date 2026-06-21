from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    INTERVIEWING = "interviewing"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    AWAITING_HANDOFF = "awaiting_handoff"
    DONE = "done"


class EventType(StrEnum):
    HACKATHON = "hackathon"
    CONFERENCE = "conference"
    SUMMIT = "summit"
    PARTY = "party"
    MEETUP = "meetup"
    WORKSHOP = "workshop"
    FESTIVAL = "festival"
    GALA = "gala"
    RETREAT = "retreat"
    OTHER = "other"


class EventFormat(StrEnum):
    IN_PERSON = "in_person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class EventDetails(BaseModel):
    name: str = ""
    type: EventType = EventType.HACKATHON
    type_label: str = ""  # free-form label when type is OTHER or user phrasing
    dates: str = ""
    location: str = ""
    expected_attendees: int = 0
    format: EventFormat = EventFormat.IN_PERSON


class Budget(BaseModel):
    total_usd: int = 0
    paid_tools_allowed: bool = False


class Audience(BaseModel):
    description: str = ""
    technical_level: str = ""
    geography: str = ""


class Aesthetic(BaseModel):
    vibe: str = ""
    theme: str = ""
    colors: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


class Ops(BaseModel):
    needs_slack: bool = True
    needs_devpost: bool = True
    registration_fields: list[str] = Field(default_factory=list)


class Outreach(BaseModel):
    sponsor_targets: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


class Artifacts(BaseModel):
    asset_urls: list[str] = Field(default_factory=list)
    asset_dir: str = ""
    promo_video_url: str = ""
    site_url: str = ""
    slack_url: str = ""
    devpost_url: str = ""
    outreach_drafts: list[str] = Field(default_factory=list)
    fallback_guides: list[str] = Field(default_factory=list)
    browserbase_session_urls: list[str] = Field(default_factory=list)
    site_verified: bool = False
    qa_screenshot_path: str = ""


class Approvals(BaseModel):
    plan_approved: bool = False
    handoff_decisions: list[dict[str, Any]] = Field(default_factory=list)


class EventProfile(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.INTERVIEWING
    event: EventDetails = Field(default_factory=EventDetails)
    budget: Budget = Field(default_factory=Budget)
    audience: Audience = Field(default_factory=Audience)
    aesthetic: Aesthetic = Field(default_factory=Aesthetic)
    ops: Ops = Field(default_factory=Ops)
    outreach: Outreach = Field(default_factory=Outreach)
    artifacts: Artifacts = Field(default_factory=Artifacts)
    approvals: Approvals = Field(default_factory=Approvals)
    interview_step: str = "event_name"
    pending_question: str | None = None
    hyperframe_id: str = Field(default_factory=lambda: str(uuid4()))

    @classmethod
    def new_session(cls, phone: str) -> EventProfile:
        session_id = phone if phone.startswith("phone:") else f"phone:{phone}"
        return cls(session_id=session_id)
