from __future__ import annotations

import json
import logging
from typing import Protocol

import redis.asyncio as aioredis

from app.config import Settings, get_settings
from app.memory.schema import EventProfile

logger = logging.getLogger(__name__)

SESSION_PREFIX = "session:"


class SessionStore(Protocol):
    async def get(self, phone: str) -> EventProfile | None: ...

    async def save(self, profile: EventProfile) -> None: ...

    async def delete(self, phone: str) -> None: ...


def _session_key(phone: str) -> str:
    normalized = phone if phone.startswith("phone:") else f"phone:{phone}"
    return f"{SESSION_PREFIX}{normalized}"


class InMemoryStore:
    """Fallback store when Redis is unavailable."""

    def __init__(self) -> None:
        self._sessions: dict[str, EventProfile] = {}

    async def get(self, phone: str) -> EventProfile | None:
        return self._sessions.get(_session_key(phone))

    async def save(self, profile: EventProfile) -> None:
        self._sessions[_session_key(profile.session_id)] = profile

    async def delete(self, phone: str) -> None:
        self._sessions.pop(_session_key(phone), None)


class RedisStore:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def get(self, phone: str) -> EventProfile | None:
        client = await self._get_client()
        raw = await client.get(_session_key(phone))
        if raw is None:
            return None
        return EventProfile.model_validate_json(raw)

    async def save(self, profile: EventProfile) -> None:
        client = await self._get_client()
        key = _session_key(profile.session_id)
        await client.set(key, profile.model_dump_json())

    async def delete(self, phone: str) -> None:
        client = await self._get_client()
        await client.delete(_session_key(phone))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class ResilientSessionStore:
    """Try Redis first; fall back to in-memory on connection failure."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._redis = RedisStore(self._settings.redis_url)
        self._fallback = InMemoryStore()
        self._using_fallback = False

    async def _ensure_backend(self) -> SessionStore:
        if self._using_fallback:
            return self._fallback
        try:
            client = await self._redis._get_client()
            await client.ping()
            return self._redis
        except Exception as exc:
            logger.warning("Redis unavailable, using in-memory store: %s", exc)
            self._using_fallback = True
            return self._fallback

    async def get(self, phone: str) -> EventProfile | None:
        store = await self._ensure_backend()
        return await store.get(phone)

    async def save(self, profile: EventProfile) -> None:
        store = await self._ensure_backend()
        await store.save(profile)

    async def delete(self, phone: str) -> None:
        store = await self._ensure_backend()
        await store.delete(phone)


_store: ResilientSessionStore | None = None


def get_session_store(settings: Settings | None = None) -> ResilientSessionStore:
    global _store
    if _store is None:
        _store = ResilientSessionStore(settings)
    return _store
