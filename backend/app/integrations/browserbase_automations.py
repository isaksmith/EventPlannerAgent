from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class SiteQAResult:
    ok: bool
    session_url: str = ""
    screenshot_path: str = ""
    registration_tested: bool = False
    slack_checked: bool = False
    detail: str = ""


def _browserbase_ready(settings: Settings) -> bool:
    return bool(
        settings.browserbase_enabled
        and settings.browserbase_api_key
        and settings.browserbase_project_id
    )


def _public_site_url(site_url: str) -> bool:
    return site_url.startswith("http://") or site_url.startswith("https://")


def _handle_ngrok_interstitial(page) -> None:  # noqa: ANN001
    for label in ("Visit Site", "Continue"):
        locator = page.get_by_role("button", name=label)
        if locator.count() > 0:
            locator.first.click(timeout=5000)
            page.wait_for_timeout(1500)
            return
        link = page.get_by_role("link", name=label)
        if link.count() > 0:
            link.first.click(timeout=5000)
            page.wait_for_timeout(1500)
            return


def _verify_site_sync(
    *,
    site_url: str,
    screenshot_path: Path,
    test_registration: bool,
    event_name: str,
    api_key: str,
    project_id: str,
) -> SiteQAResult:
    from browserbase import Browserbase
    from playwright.sync_api import sync_playwright

    bb = Browserbase(api_key=api_key)
    session = bb.sessions.create(
        project_id=project_id,
        browser_settings={"recordSession": True, "logSession": True},
    )
    session_url = f"https://browserbase.com/sessions/{session.id}"
    registration_tested = False
    detail_parts: list[str] = []

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(session.connect_url)
        page = browser.contexts[0].pages[0]
        page.goto(site_url, wait_until="domcontentloaded", timeout=90_000)
        if "ngrok" in site_url:
            _handle_ngrok_interstitial(page)

        page.wait_for_timeout(2000)
        body = page.inner_text("body")
        has_register = "Register" in body or page.locator("#register").count() > 0
        if not has_register:
            detail_parts.append("Register section not found")

        if test_registration and has_register:
            page.locator('input[name="name"]').first.fill("Marquee QA Bot", timeout=10_000)
            page.locator('input[name="email"]').first.fill("qa@marquee.test", timeout=10_000)
            team = page.locator('input[name="team"]')
            if team.count() > 0:
                team.first.fill("solo", timeout=5000)
            submit = page.locator('#reg-form button[type="submit"]')
            if submit.count() == 0:
                submit = page.get_by_role("button", name="Register")
            submit.first.click(timeout=10_000)
            page.wait_for_timeout(2000)
            after = page.inner_text("body")
            registration_tested = "registered" in after.lower()
            if registration_tested:
                detail_parts.append("Test registration submitted")
            else:
                detail_parts.append("Registration submit did not show confirmation")

        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    ok = has_register and (registration_tested or not test_registration)
    return SiteQAResult(
        ok=ok,
        session_url=session_url,
        screenshot_path=str(screenshot_path),
        registration_tested=registration_tested,
        detail="; ".join(detail_parts) or f"Verified {event_name or 'event'} registration page",
    )


def _verify_slack_sync(*, slack_url: str, api_key: str, project_id: str) -> tuple[bool, str]:
    from browserbase import Browserbase
    from playwright.sync_api import sync_playwright

    bb = Browserbase(api_key=api_key)
    session = bb.sessions.create(project_id=project_id)
    session_url = f"https://browserbase.com/sessions/{session.id}"

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(session.connect_url)
        page = browser.contexts[0].pages[0]
        response = page.goto(slack_url, wait_until="domcontentloaded", timeout=60_000)
        status = response.status if response else 0
        title = page.title()
        browser.close()

    ok = status < 400 and bool(title)
    detail = f"Slack page loaded (HTTP {status}, title={title[:40]})"
    return ok, f"{detail} · {session_url}"


async def verify_registration_site(
    *,
    site_url: str,
    screenshot_path: Path,
    test_registration: bool,
    event_name: str,
    settings: Settings | None = None,
) -> SiteQAResult | None:
    cfg = settings or get_settings()
    if not _browserbase_ready(cfg) or not _public_site_url(site_url):
        return None
    try:
        return await asyncio.to_thread(
            _verify_site_sync,
            site_url=site_url,
            screenshot_path=screenshot_path,
            test_registration=test_registration,
            event_name=event_name,
            api_key=cfg.browserbase_api_key,
            project_id=cfg.browserbase_project_id,
        )
    except ImportError:
        logger.warning("browserbase/playwright not installed — pip install browserbase playwright")
        return None
    except Exception as exc:
        logger.warning("Browserbase site QA failed: %s", exc)
        return SiteQAResult(ok=False, detail=str(exc))


async def verify_slack_link(
    *,
    slack_url: str,
    settings: Settings | None = None,
) -> tuple[bool, str] | None:
    cfg = settings or get_settings()
    if not _browserbase_ready(cfg) or not cfg.browserbase_verify_slack or not _public_site_url(slack_url):
        return None
    try:
        return await asyncio.to_thread(
            _verify_slack_sync,
            slack_url=slack_url,
            api_key=cfg.browserbase_api_key,
            project_id=cfg.browserbase_project_id,
        )
    except ImportError:
        return None
    except Exception as exc:
        logger.warning("Browserbase Slack check failed: %s", exc)
        return (False, str(exc))
