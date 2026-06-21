from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import httpx

from app.config import Settings, get_settings
from app.integrations.midjourney import build_design_seed
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)

FAL_QUEUE_BASE = "https://queue.fal.run"


def build_promo_prompt(profile: EventProfile) -> str:
    name = profile.event.name or "Your Event"
    vibe = profile.aesthetic.vibe or "energetic and modern"
    location = profile.event.location or "campus"
    return (
        f"Cinematic 5-second event promo for '{name}', {profile.event.type.value}, "
        f"{vibe} aesthetic, {location}, dynamic camera motion, "
        f"crowd energy, bold typography moments, festival lighting, no logos"
    )


def _fal_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}


def _extract_video_url(result: dict) -> str | None:
    video = result.get("video")
    if isinstance(video, dict) and video.get("url"):
        return str(video["url"])
    if isinstance(result.get("video_url"), str):
        return result["video_url"]
    return None


async def _poll_fal_result(
    *,
    model_id: str,
    request_id: str,
    api_key: str,
    status_url: str | None,
    response_url: str | None,
    timeout_seconds: float,
) -> dict:
    headers = _fal_headers(api_key)
    base = f"{FAL_QUEUE_BASE}/{model_id}"
    status_endpoint = status_url or f"{base}/requests/{request_id}/status"
    result_endpoint = response_url or f"{base}/requests/{request_id}"

    deadline = time.monotonic() + timeout_seconds
    async with httpx.AsyncClient(timeout=60.0) as client:
        while time.monotonic() < deadline:
            status_resp = await client.get(status_endpoint, headers=headers, params={"logs": 0})
            status_resp.raise_for_status()
            payload = status_resp.json()
            state = payload.get("status")
            if state == "COMPLETED":
                result_resp = await client.get(result_endpoint, headers=headers)
                result_resp.raise_for_status()
                body = result_resp.json()
                return body.get("response", body)
            if state in {"FAILED", "CANCELLED"}:
                raise RuntimeError(f"Pika/fal job {state}: {payload}")
            await asyncio.sleep(3)
    raise TimeoutError(f"Pika generation timed out after {timeout_seconds}s")


async def _submit_fal_job(model_id: str, arguments: dict, api_key: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{FAL_QUEUE_BASE}/{model_id}",
            headers=_fal_headers(api_key),
            json=arguments,
        )
        response.raise_for_status()
        return response.json()


async def _upload_local_image(path: Path, api_key: str) -> str:
    def _upload() -> str:
        import fal_client

        return fal_client.upload_file(str(path))

    try:
        return await asyncio.to_thread(_upload)
    except ImportError as exc:
        raise RuntimeError("fal-client required for image-to-video uploads") from exc


async def _download_video(url: str, dest: Path) -> Path:
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)
        return dest


def _hero_image_path(profile: EventProfile) -> Path | None:
    if not profile.artifacts.asset_dir:
        return None
    asset_dir = Path(profile.artifacts.asset_dir)
    for name in (
        "invite_cover.webp",
        "invite_cover.png",
        "invite_hero.webp",
        "invite_hero.png",
        "hero.png",
        "hero.jpg",
        "hero.webp",
        "logo.png",
    ):
        candidate = asset_dir / name
        if candidate.is_file():
            return candidate
    return None


async def _call_pika_api(profile: EventProfile, settings: Settings) -> str | None:
    if not settings.pika_enabled or not settings.pika_api_key:
        return None

    prompt = build_promo_prompt(profile)
    hero = _hero_image_path(profile) if settings.pika_use_hero_image else None
    model_id = settings.pika_model_image if hero else settings.pika_model_text

    arguments: dict = {
        "prompt": prompt,
        "duration": settings.pika_duration_seconds,
        "resolution": settings.pika_resolution,
        "aspect_ratio": settings.pika_aspect_ratio,
    }
    if hero:
        arguments["image_url"] = await _upload_local_image(hero, settings.pika_api_key)

    submit = await _submit_fal_job(model_id, arguments, settings.pika_api_key)
    result = await _poll_fal_result(
        model_id=model_id,
        request_id=str(submit["request_id"]),
        api_key=settings.pika_api_key,
        status_url=submit.get("status_url"),
        response_url=submit.get("response_url"),
        timeout_seconds=float(settings.pika_timeout_seconds),
    )
    return _extract_video_url(result)


def _write_stub_promo(asset_dir: Path, profile: EventProfile) -> str:
    asset_dir.mkdir(parents=True, exist_ok=True)
    promo_path = asset_dir / "promo.txt"
    promo_path.write_text(
        f"Promo clip stub for {profile.event.name}\n"
        f"Prompt: {build_promo_prompt(profile)}\n"
        f"Seed: {build_design_seed(profile)[:200]}\n",
        encoding="utf-8",
    )
    return str(promo_path)


async def generate_promo_clip(
    profile: EventProfile,
    settings: Settings | None = None,
) -> EventProfile:
    tracer = get_tracer()
    cfg = settings or get_settings()
    asset_dir = Path(profile.artifacts.asset_dir) if profile.artifacts.asset_dir else None

    async with tracer.span("pika.generate", session_id=profile.session_id):
        video_ref: str | None = None
        try:
            remote_url = await _call_pika_api(profile, cfg)
            if remote_url and asset_dir:
                asset_dir.mkdir(parents=True, exist_ok=True)
                local_path = await _download_video(remote_url, asset_dir / "promo.mp4")
                video_ref = str(local_path)
            elif remote_url:
                video_ref = remote_url
        except Exception as exc:
            logger.warning("Pika generation failed for %s: %s", profile.session_id, exc)

        if video_ref is None:
            if asset_dir is None:
                asset_dir = Path(cfg.assets_output_dir) / profile.session_id.replace(":", "_").replace("+", "")
                asset_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Pika stub: promo placeholder for %s", profile.session_id)
            video_ref = _write_stub_promo(asset_dir, profile)

        profile.artifacts.promo_video_url = video_ref
    return profile
