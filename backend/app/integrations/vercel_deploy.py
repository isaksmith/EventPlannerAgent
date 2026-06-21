from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_UPLOAD_DENYLIST = {
    "event_profile.json",
    "SITE_BRIEF.md",
    "registrations.jsonl",
    "setup-guides.txt",
}

_VERCEL_API = "https://api.vercel.com"
_SITE_PROJECT_PREFIX = "marquee-site-"


def _project_name(slug: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", slug.lower())
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    return f"orchestrate-{sanitized}"


def _iter_upload_files(build_dir: Path):
    for item in build_dir.rglob("*"):
        if item.is_file() and item.name not in _UPLOAD_DENYLIST:
            yield item


def _inject_serverless_registration(
    build_dir: Path, settings: Settings, *, event_name: str, site_slug: str
) -> None:
    api_dir = build_dir / "api"
    api_dir.mkdir(exist_ok=True)

    cfg = {
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_KEY": settings.supabase_service_role_key,
        "EVENT_NAME": event_name,
        "SITE_SLUG": site_slug,
    }

    register_js = f"""module.exports = async (req, res) => {{
  const CFG = {json.dumps(cfg)};
  if (req.method !== "POST") {{
    res.status(405).json({{error: "Method not allowed"}});
    return;
  }}
  const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
  if (!CFG.SUPABASE_URL || !CFG.SUPABASE_KEY) {{
    const fs = require("fs");
    const path = require("path");
    const file = path.join(process.cwd(), "registrations.jsonl");
    fs.appendFileSync(file, JSON.stringify(body) + "\\n");
    res.status(200).json({{ok: true, stored: "jsonl"}});
    return;
  }}
  try {{
    const r = await fetch(`${{CFG.SUPABASE_URL}}/rest/v1/registrations`, {{
      method: "POST",
      headers: {{
        apikey: CFG.SUPABASE_KEY,
        Authorization: `Bearer ${{CFG.SUPABASE_KEY}}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      }},
      body: JSON.stringify({{
        name: body.name || "",
        email: body.email || "",
        team: body.team || "",
        track: body.track || "",
        event_name: CFG.EVENT_NAME,
        site_slug: CFG.SITE_SLUG,
        created_at: new Date().toISOString(),
      }}),
    }});
    if (!r.ok) {{
      const text = await r.text();
      res.status(502).json({{error: "supabase", detail: text}});
      return;
    }}
    res.status(200).json({{ok: true}});
  }} catch (e) {{
    res.status(500).json({{error: "exception", detail: String(e)}});
  }}
}};
"""
    (api_dir / "register.js").write_text(register_js, encoding="utf-8")

    vercel_json = {
        "version": 2,
        "rewrites": [{"source": "/api/register", "destination": "/api/register"}],
        "functions": {"api/register.js": {"memory": 128}},
    }
    (build_dir / "vercel.json").write_text(
        json.dumps(vercel_json, indent=2), encoding="utf-8"
    )


async def _create_project(client: httpx.AsyncClient, name: str, team_id: str, token: str) -> str | None:
    resp = await client.post(
        f"{_VERCEL_API}/v11/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "framework": None},
        params={"teamId": team_id} if team_id else {},
    )
    if resp.status_code == 200:
        return resp.json()["id"]
    if resp.status_code == 409:
        list_resp = await client.get(
            f"{_VERCEL_API}/v9/projects",
            headers={"Authorization": f"Bearer {token}"},
            params={"teamId": team_id} if team_id else {},
        )
        if list_resp.status_code == 200:
            for proj in list_resp.json().get("projects", []):
                if proj["name"] == name:
                    return proj["id"]
    return None


async def _disable_deployment_protection(client: httpx.AsyncClient, project_id: str, team_id: str, token: str) -> None:
    await client.patch(
        f"{_VERCEL_API}/v9/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"ssoProtection": None},
        params={"teamId": team_id} if team_id else {},
    )


async def _create_deployment(client: httpx.AsyncClient, project_name: str, files: list[dict], team_id: str, token: str) -> str | None:
    resp = await client.post(
        f"{_VERCEL_API}/v13/deployments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": project_name,
            "project": project_name,
            "files": files,
            "target": "production",
            "projectSettings": {"framework": None},
        },
        params={"teamId": team_id} if team_id else {},
    )
    if resp.status_code in (200, 201):
        data = resp.json()
        return data.get("url") or data.get("alias", [None])[0]
    logger.warning("Vercel deploy failed: %s %s", resp.status_code, resp.text[:200])
    return None


async def deploy_site_to_vercel(
    build_dir: Path,
    *,
    slug: str,
    event_name: str,
    settings: Settings,
) -> str | None:
    if not settings.vercel_token:
        logger.info("Vercel deploy skipped — no VERCEL_TOKEN set")
        return None

    _inject_serverless_registration(build_dir, settings, event_name=event_name, site_slug=slug)

    project_name = _project_name(slug)
    team_id = settings.vercel_team_id
    token = settings.vercel_token

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            project_id = await _create_project(client, project_name, team_id, token)
            if not project_id:
                logger.warning("Could not create/find Vercel project %s", project_name)
                return None

            await _disable_deployment_protection(client, project_id, team_id, token)

            files_payload = []
            for f in _iter_upload_files(build_dir):
                data = base64.b64encode(f.read_bytes()).decode()
                rel = str(f.relative_to(build_dir))
                files_payload.append({"file": rel, "data": data, "encoding": "base64"})

            deploy_url = await _create_deployment(client, project_name, files_payload, team_id, token)
            if deploy_url:
                url = deploy_url if deploy_url.startswith("https://") else f"https://{deploy_url}"
                logger.info("Vercel deploy URL: %s", url)
                return url
    except Exception as e:
        logger.warning("Vercel deploy exception: %s", e)

    return None
