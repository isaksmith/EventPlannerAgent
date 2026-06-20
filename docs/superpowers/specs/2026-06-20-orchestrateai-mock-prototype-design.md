# OrchestrateAI — Mock Prototype Design

> **Date:** 2026-06-20
> **Author:** Michael Goldberg (+ Claude Code)
> **Source of truth:** [`PRD.md`](../../../PRD.md)
> **Status:** Approved — ready to build

## Purpose

A **front-end-only mock prototype** of the OrchestrateAI platform. Every integration
described in the PRD is **faked** but rendered the way it could plausibly look in the
real product. This is **not the final product** — it is a visual skeleton / template /
shared reference that the team builds off of. Each teammate replaces one fake panel
with its real integration.

Non-goal: no real network calls, no real backend, no real SMS, no real LLM. Everything
is scripted and mocked.

## Audience

- The team building OrchestrateAI for the UC Berkeley AI Hackathon 2026.
- Each integration owner uses their panel as the visual contract for what they build.

## Stack

- **Single self-contained `index.html`** at the repo root.
- HTML + Tailwind (CDN) + vanilla JS. No build step, no install. Double-click to open.
- **Rationale:** zero-install sharing (no Node/npm dependency for teammates), trivially
  portable, and mirrors the PRD's own output (Claude Code generates HTML/Tailwind).
- All fake behavior lives in one `MockIntegrations` namespace in a `<script>` block.
  Each integration is a named async function returning fake data on a timer:
  `mockSai`, `mockRedis`, `mockMidjourney`, `mockPika`, `mockClaudeCode`,
  `mockBrowserbase`, `mockOutreach`, `mockArize`.
- **The seam map:** every mock function carries a `// TODO[teammate]: replace with
  real <X> call` banner. Swapping fake → real = "find the function, replace the body."

## Layout — split "command center"

```
┌──────────────┬────────────────────────────────────────────┐
│  📱 PHONE     │  PHASE RAIL: 0 ─ 1 ─ 2 ─ 3 ─ 4 ─ 5         │
│  (SMS thread)│ ┌──────────┬──────────┬───────────────────┐ │
│              │ │ Sai      │ Redis    │ Autonomy tiers    │ │
│  organizer   │ │ dispatch │ state    │ T1 / T2 / T3      │ │
│  ↔ Orchestr. │ ├──────────┼──────────┴───────────────────┤ │
│              │ │ Creative │ Code + Deploy (site preview) │ │
│  approval    │ │ pipeline │                              │ │
│  gates ✋    │ ├──────────┼──────────┬───────────────────┤ │
│  tappable    │ │ Browser  │ Outreach │ Arize trace       │ │
│  APPROVE/    │ │ base     │ drafts   │ (spans/latency)   │ │
│  SEND/SKIP   │ └──────────┴──────────┴───────────────────┘ │
└──────────────┴────────────────────────────────────────────┘
```

- **Left third — phone:** iPhone-style frame, SMS thread (the only thing the human
  touches). Approval gates render as tappable `APPROVE` / `SEND` / `SKIP` bubbles.
- **Right two-thirds — cockpit:**
  - **Phase rail** across the top: Phase 0 → 5, current phase highlighted.
  - **Sai dispatcher:** current intent + state-machine node.
  - **Redis state:** the Event Profile JSON (schema from PRD §8) filling in field-by-field.
  - **Creative pipeline (Midjourney/Pika):** logo tile, color tokens, bg graphic, promo
    clip placeholders.
  - **Code + Deploy (Claude Code → Vercel):** build log → a **mini rendered registration
    site preview** → fake Vercel URL.
  - **Browserbase:** Slack channels + Devpost draft "provisioning," including the
    graceful-failure fallback path.
  - **Outreach:** Tier-3 sponsor email drafts — draft-only, never auto-send.
  - **Arize trace:** ticking list of spans (node, latency ms, token/cost).
  - **Autonomy tier legend:** Tier 1 auto / Tier 2 confirm / Tier 3 handoff, highlighting
    live as the flow hits each tier.

## Demo flow — scripted, one canned event

Canned event: **"UC Berkeley AI Hackathon, 200 people, 6 weeks."**

Controls: **Next** (step forward), **Auto-play** (hands-free for pitches), **Reset**.

SMS replies are pre-baked tappable choices so a live demo never dead-ends. The script
walks all six PRD phases and deliberately fires the moments that ARE the success metrics
(PRD §11):

1. **Phase 0 — Initiation:** organizer texts `PLAN`; Sai opens a session, Redis profile created.
2. **Phase 1 — Interview:** ~6–8 branched questions; each answer writes into Redis live.
3. **Phase 2 — Consensus gate ✋:** Sai texts the profile summary; user taps `APPROVE`.
4. **Phase 3 — Calibrated execution:** fan-out. Creative (Tier 1) → Code+Deploy (Tier 1)
   → Browserbase (Tier 1, **with one simulated failure that degrades gracefully**) →
   Outreach drafts (Tier 3, draft-only). Progress texts keep the SMS loop alive.
5. **Phase 4 — High-stakes handoff ✋:** Tier-3 gate — drafted sponsor emails / domain
   purchase; user taps `SEND` / `EDIT` / `SKIP` / `BUY`.
6. **Phase 5 — Final delivery:** wrap-up text: site URL + Slack + Devpost + asset folder +
   pending drafts.

Three demoed guarantees (map to PRD §11): both approval gates fire; one graceful
third-party failure; a live Arize trace with latency/cost.

## What's explicitly faked (but looks real)

- A rendered **mini registration site** (real-ish, not a grey box).
- Real-looking color swatches / logo tile / bg graphic.
- Plausible Arize latency + token/cost numbers.
- A believable Redis JSON growing live.
- No real network calls anywhere.

## Integration seam ownership (for the team)

| Panel / mock fn | PRD layer | Teammate swaps in |
|---|---|---|
| `mockSai` | Simular Sai / Simulang | real dispatcher + Hyperframes |
| Phone SMS I/O | Poke API | real SMS/iMessage webhook loop |
| `mockRedis` | Redis | real session/state store |
| `mockMidjourney` / `mockPika` | Midjourney / Pika | real asset generation |
| `mockClaudeCode` | Claude Code / Opencode → Vercel | real codegen + deploy |
| `mockBrowserbase` | Browserbase | real headless provisioning |
| `mockOutreach` | (drafting) | real draft generation (still no auto-send) |
| `mockArize` | Arize AI | real tracing/observability |

## Out of scope

- Any real integration, backend, auth, persistence, or deployment.
- Multi-event / multi-tenant flows.
- Mobile-responsive polish beyond "looks fine on a laptop for the demo."
