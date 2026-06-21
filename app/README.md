# Marquee

Plan a whole event by chat. **This is a front-end prototype** — the UI and flow
are real, but every integration is **mocked behind a typed seam**. It's built so
you can wire real backends in without touching the UI.

## Run it

```bash
cd app
npm install
npm run dev      # http://localhost:5173
```

Drive the demo with **Auto-play** (or **Next** / Spacebar). Approve in the chat
at the two gates. **Reset** restarts.

## Stack

React + Vite + TypeScript + Tailwind. No backend, no network calls.

## How it's wired (read this before integrating)

```
src/
  types.ts                     # shared domain types (EventProfile, BrandKit, …)
  integrations/
    contracts.ts               # ★ the interfaces YOU implement (Sai, Redis, …)
    mocks.ts                   # fake implementations (all data is canned)
    index.ts                   # ★ getIntegrations() — swap mocks → real HERE
  orchestrator/
    demoScript.ts              # the canned timeline (the "fake engine")
    useOrchestrator.ts         # drives the flow; calls the integrations
  components/                  # Header, ChatPanel, Tiles, BehindTheScenes
  App.tsx                      # layout: chat + tiling deliverable panels
```

### To plug in a real backend

1. **Implement the contracts.** Each interface in `integrations/contracts.ts` is
   one service: `SaiAgent`, `MemoryStore` (Redis), `BrandService` (Midjourney),
   `DeployService` (Claude Code → Vercel), `BrowserbaseService`,
   `OutreachService`, `Tracer` (Arize). The mocks in `mocks.ts` show the exact
   return shapes — match them.

2. **Wire them in one place.** In `integrations/index.ts`, return your real
   implementations from `getIntegrations()` instead of the mocks. **The UI never
   changes** — it only depends on the `Integrations` interface.

3. **Swap the engine.** `orchestrator/useOrchestrator.ts` currently plays
   `demoScript.ts`. For the real product, replace its scripted `advance()` with a
   live loop where Sai drives the conversation — but keep calling the same
   `integrations.*` services and updating the same state shape, so the UI keeps
   working.

Everything mockable is marked `// TODO[teammate]` in `mocks.ts`.

### Notes
- All integration calls are `async` (they're I/O in production).
- Browserbase must **degrade gracefully** — return `{ ok: false, fallback }`,
  never throw (the UI relies on this; see the Devpost path).
- Outreach is **draft-only** — never auto-send.
- SMS/iMessage is intentionally **not** here; it's a later optional layer in
  front of Sai. Marquee is desktop-first.
