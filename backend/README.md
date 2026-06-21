# OrchestrateAI Backend

Python FastAPI backend for the OrchestrateAI SMS event-planning orchestrator (Milestone 1).

## Prerequisites

- Python 3.11+
- [Optional] Docker & Docker Compose for Redis

## Quick start (local)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health`

## With Docker Compose (Redis + backend)

```bash
cd backend
docker compose up --build
```

## Poke integration (MCP tunnel — Option 1)

OrchestrateAI exposes an MCP server at **`http://localhost:8000/mcp`** (Streamable HTTP). Poke calls your tools when the user chats in iMessage.

### Tools

| Tool | Purpose |
|------|---------|
| `start_event_planning` | Begin session (like texting `PLAN`) |
| `send_planning_message` | Send user reply / `APPROVE` / `ALL-SKIP` |
| `get_planning_status` | Check current phase |

### Setup

**Terminal 1 — backend**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Poke tunnel** (requires one-time login)

```bash
npx poke@latest login   # once — opens browser / pastes Kitchen API key
npx poke@latest tunnel http://localhost:8000/mcp -n "OrchestrateAI"
```

Or use the helper script:

```bash
./scripts/connect-poke.sh tunnel
```

**Alternative — ngrok (no `poke login`)** if ngrok already forwards port 8000:

```bash
./scripts/connect-poke.sh remote
```

Then register **`https://stegosaur-setting-mammogram.ngrok-free.dev/mcp`** at [poke.com/settings/connections/integrations/new](https://poke.com/settings/connections/integrations/new) (Streamable HTTP).

### Try it in iMessage

Text Poke something like:

> Use the OrchestrateAI integration to start event planning, then help me answer the interview questions.

Or explicitly:

> Call OrchestrateAI's `start_event_planning` tool, then use `send_planning_message` for each of my answers.

If Poke uses a stale integration name, send `clearhistory` to Poke and retry.

### Alternative: register remote MCP

If using ngrok instead of `poke tunnel`:

1. Start backend + `ngrok start orchestrateai` (port 8000)
2. Go to [poke.com/settings/connections/integrations/new](https://poke.com/settings/connections/integrations/new)
3. **MCP Server URL:** `https://YOUR-DOMAIN/mcp`
4. **Name:** OrchestrateAI

## Simulate an inbound SMS webhook

```bash
curl -X POST http://localhost:8000/webhooks/poke \
  -H "Content-Type: application/json" \
  -d '{"from": "+15551234567", "body": "PLAN"}'
```

Continue the interview by sending answers to the same `from` number:

```bash
curl -X POST http://localhost:8000/webhooks/poke \
  -H "Content-Type: application/json" \
  -d '{"from": "+15551234567", "body": "Berkeley AI Hackathon"}'
```

When you receive the plan summary, reply `APPROVE` to trigger the Phase 3 execution stub.

## Tests

```bash
cd backend
pip install -e ".[dev]"
pytest
```

## Architecture (Milestone 1–2)

| Module | Role |
|---|---|
| `app/mcp/server.py` | MCP tools for Poke (Streamable HTTP at `/mcp`) |
| `app/webhooks/poke.py` | Inbound SMS webhook (curl / legacy harness) |
| `app/orchestrator/sai.py` | Sai dispatcher (phases 0–5) |
| `app/orchestrator/state_machine.py` | Branched interview (6–10 questions) |
| `app/orchestrator/approval_gate.py` | Phase 2 APPROVE / amend gate |
| `app/orchestrator/executor.py` | Phase 3 fan-out + Phase 4/5 handoff messages |
| `app/integrations/midjourney.py` | Brand assets — OpenRouter images → Midjourney MCP → SVG stubs |
| `app/integrations/midjourney_mcp.py` | Midjourney MCP client (fallback) |
| `app/integrations/openrouter_images.py` | OpenRouter image generation (primary) |
| `app/integrations/pika.py` | Promo clip via Pika on fal.ai (text/image-to-video) |
| `app/integrations/claude_code.py` | HTML/Tailwind site build + optional Vercel deploy |
| `app/integrations/browserbase.py` | Slack API + Browserbase post-build QA (site + Slack) |
| `app/integrations/browserbase_automations.py` | Playwright sessions: site verify, test registration |
| `app/integrations/outreach.py` | Tier-3 draft-only sponsor/marketing emails |
| `app/integrations/token_compression.py` | Context compression for LLM calls |
| `app/memory/redis_store.py` | Session CRUD (Redis + in-memory fallback) |
| `app/observability/arize.py` | Tracing wrapper (no-op when disabled) |

Generated sites and assets land in `var/builds/` and `var/assets/` (gitignored).

## End-to-end demo flow

1. Text `PLAN` → complete interview (~10 questions)
2. Reply `APPROVE` on the plan summary
3. Receive progress texts while assets, site, and platforms build
4. Review handoff message — reply `ALL-SKIP` to finish (Tier-3 SEND/EDIT/SKIP also supported)

## Live site URLs (demo)

Set in `.env`:

```
PUBLIC_BASE_URL=https://stegosaur-setting-mammogram.ngrok-free.dev
```

After `APPROVE`, the registration site is served at:

```
https://<your-ngrok-domain>/sites/<session-id>/
```

View execution traces at `GET /admin/traces` (for pitch / debugging).

## Arize AI (observability)

Traces export to [Arize AX](https://arize.com) when credentials are set in `.env`:

```
ARIZE_ENABLED=true
ARIZE_API_KEY=ak-...
ARIZE_SPACE_ID=...
ARIZE_PROJECT_NAME=orchestrateai
```

Install tracing deps (once disk space allows):

```bash
cd backend
source .venv/bin/activate
pip install arize-otel opentelemetry-instrumentation-httpx
```

Configure the AX CLI profile from `.env`:

```bash
python scripts/setup_arize_auth.py
# then: pipx install arize-ax-cli  (or uv tool install arize-ax-cli)
ax profiles show && ax projects list
```

Every orchestrator/integration span (`intent.classify`, `midjourney.logo`, `claude.build`, …) is emitted as an OpenTelemetry span when Arize is enabled. The Marquee dashboard polls `GET /admin/traces` for the live trace panel.

## Site generation (UI/UX Pro Max + OpenRouter)

**Poke handles chat only** (interview, APPROVE, handoff). **Every APPROVE** builds a custom registration site:

1. Seed `app/templates/event_site/index.html`
2. **UI/UX Pro Max** design system search (`skills/ui-ux-pro-max/`) from event profile
3. **OpenRouter** site coder (`openai/gpt-oss-120b:free` by default) customizes `index.html`
4. OpenCode CLI optional fallback · Marquee template if both fail

Sites are served at `/sites/{slug}/`.

### Setup

Add to `.env`:

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-oss-120b:free
SITE_CODER_ENABLED=true
UI_UX_PRO_MAX_ENABLED=true
```

### Regenerate a site manually

```bash
cd backend
source .venv/bin/activate
python -m app.cli.generate_site --reseed-template --slug phone_dashboard-demo
python -m app.cli.generate_site --slug phone_dashboard-demo   # full UI/UX + OpenRouter pass
```

Optional OpenCode fallback: set `OPENCODE_ENABLED=true` and install [OpenCode CLI](https://opencode.ai/install).

## Midjourney (brand assets)

Marquee generates invite images during APPROVE:

1. **OpenRouter image API** (primary) — `google/gemini-3-pro-image` via chat completions
2. **Midjourney MCP** (fallback) — official `https://mcp.midjourney.com/mcp`
3. **SVG stubs** — when both are unavailable

Set `OPENROUTER_API_KEY` and `OPENROUTER_IMAGE_PRIMARY=true` (default). See [OpenRouter image generation](https://openrouter.ai/docs/guides/overview/multimodal/image-generation).

### Cursor / Claude (manual image gen)

Project `.cursor/mcp.json` includes:

```json
{
  "mcpServers": {
    "midjourney": {
      "url": "https://mcp.midjourney.com/mcp"
    }
  }
}
```

Reload Cursor MCP, then ask to generate an image. A browser opens once to log in to Midjourney.

### Backend (automatic on APPROVE)

1. Create a Midjourney account and apply the hackathon coupon (Mega annual).
2. Authenticate once:

   ```bash
   cd backend
   source .venv/bin/activate
   python scripts/auth_midjourney_mcp.py
   ```

3. Enable in `.env`:

   ```
   MIDJOURNEY_MCP_ENABLED=true
   MIDJOURNEY_MCP_USE_OAUTH=true
   MIDJOURNEY_MCP_URL=https://mcp.midjourney.com/mcp
   ```

Without auth, the executor falls back to local SVG placeholders (demo still works).

Docs: [Midjourney MCP](https://www.midjourney.com/mcp-docs) · [Prompting guide](https://docs.midjourney.com/)

## Pika (promo video)

Event promo clips use **Pika models on [fal.ai](https://fal.ai)** (official Pika API path).

1. Create a [fal.ai](https://fal.ai) account and copy your API key.
2. Add to `.env`:

   ```
   PIKA_ENABLED=true
   PIKA_API_KEY=your-fal-api-key
   ```

3. On APPROVE, Marquee generates a ~5s promo after brand assets. If `hero.png` exists (Midjourney), it uses **image-to-video**; otherwise **text-to-video**.

Output: `var/assets/<session>/promo.mp4` (fallback: `promo.txt` stub without key).

Docs: [Pika on fal](https://fal.ai/models/fal-ai/pika/v2.2/text-to-video) · [pika.art/api](https://pika.art/api)

## Slack setup

OrchestrateAI uses a **pre-created workspace** (`EventPlannerAgent`) and the Slack Web API to create event channels on APPROVE.

1. Add to `.env`:
   ```
   SLACK_ACCESS_TOKEN=xoxb-...   # Bot User OAuth Token (recommended)
   SLACK_INVITE_URL=https://join.slack.com/t/...   # optional join link for SMS
   DEVPOST_ENABLED=false
   ```
2. At [api.slack.com/apps](https://api.slack.com/apps) → **EventPlannerAgent** → **OAuth & Permissions**, add **Bot Token Scopes**:
   - `channels:manage`
   - `channels:read`
   - `chat:write`
3. **Reinstall to workspace** and copy the **Bot User OAuth Token** (`xoxb-...`) into `SLACK_ACCESS_TOKEN`.
4. Verify:
   ```bash
   ./scripts/test-slack.sh
   ./scripts/test-slack.sh http://127.0.0.1:8000 --provision
   ```
   Or open `GET /admin/slack/test?provision=true`.

Without Redis, sessions persist in memory only (fine for local dev/tests).

## Environment variables

See `.env.example`. No real API keys are required for local development — outbound SMS is logged as stub output.
