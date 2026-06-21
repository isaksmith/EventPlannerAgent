# OrchestrateAI — Product Requirements Document (PRD)

> **Working title:** OrchestrateAI
> **Target event:** UC Berkeley AI Hackathon 2026
> **Repo:** https://github.com/isaksmith/EventPlannerAgent.git
> **Doc owner:** Michael Goldberg (Product / Planning)
> **Status:** Draft v1 — for team review
> **One-liner:** A stateful, multi-agent orchestration engine that turns a single SMS conversation into a fully deployed, large-scale event.

---

## 1. Executive Summary

Planning a major event from scratch — a 200-person hackathon, a conference, a summit — is brutal not because any one task is hard, but because the work is **fragmented across a dozen disconnected verticals** (branding, web development, registration, platform setup, sponsor outreach, marketing). The organizer's own working memory is the only thing holding the dependencies together.

For a solo founder or a single org president, that **integration load is the actual job** — and it's what makes the whole thing take weeks.

OrchestrateAI replaces that human coordination layer with an **agent network**. The organizer texts a number, gets interviewed conversationally about their event, and the system builds a structured event profile, pauses to confirm it, and then executes. From that single approval it generates branded visual assets, builds and deploys a live registration site, provisions the community Slack and Devpost setup, and compiles sponsor and marketing outreach — collapsing weeks of cross-platform work into a few hours.

Critically, the agent **calibrates its autonomy to the stakes of each task**: it acts on its own for reversible, low-risk work, and deliberately stops to hand control back to the human for decisions that carry real money or real relationships. The result is an event planner that holds the entire dependency graph so the human no longer has to be the integration layer — **they just approve, and the event assembles itself.**

---

## 2. Problem Statement

| Dimension | Today (manual) | With OrchestrateAI |
|---|---|---|
| **Who does it** | One organizer mentally tracks every vertical | Agent network holds the dependency graph |
| **Time** | Weeks of cross-platform coordination | A few hours |
| **Failure mode** | A dropped dependency (forgot to set up Slack, site not ready for launch) cascades | Orchestrator tracks state; nothing is forgotten |
| **Cognitive load** | Organizer *is* the integration layer | Organizer just approves at checkpoints |
| **Tooling** | A dozen disconnected SaaS tabs | One SMS thread |

**Core insight:** The hard part of event planning is not any single task — it's the *integration* of fragmented work and the *memory* of how it all connects. That is precisely what an orchestration engine with persistent state is good at.

---

## 3. Goals & Non-Goals

### 3.1 Goals
- Let an organizer plan and launch an event **entirely over SMS**, with no dashboard required.
- Build a **structured, persistent event profile** from a conversational interview.
- **Execute** the reversible build work autonomously: branding assets, deployed registration site, Slack/Devpost setup, drafted outreach.
- **Calibrate autonomy to stakes** — auto-run low-risk work, stop and ask for high-stakes (money/relationship) decisions.
- Deliver a **single hand-off** at the end: live site URL + credentials + drafts, via SMS.

### 3.2 Non-Goals (for the hackathon build)
- Not a full event-management/ticketing CRM (no day-of check-in, no payments processing).
- Not autonomously *sending* sponsor emails or *spending* money without explicit human approval.
- Not a multi-tenant SaaS with billing — single-organizer demo flow is sufficient for v1.
- Not replacing human judgment on brand/sponsor relationships — it drafts; the human sends.

---

## 4. Users & Primary Use Case

**Primary persona — "The Solo Organizer":** a club president, solo founder, or community lead who has to stand up a large event with little/no team and limited time. Technical ability varies; comfort with SMS is universal.

**Primary use case:** "I'm running a 200-person hackathon in 6 weeks and I'm doing it alone. I text a number, answer some questions, approve a summary, and a few hours later I have a live registration site, branding, a Slack, a Devpost draft, and sponsor emails ready to send."

---

## 5. System Architecture & Integration Matrix

The platform uses a **decoupled, event-driven multi-agent architecture** where **Simular Sai** acts as the central cognitive dispatcher, routing sub-tasks to specialized micro-agents and tools.

| Layer | Technology | Functional Responsibility |
|---|---|---|
| **Inbound Interface** | **Poke API** | Handles SMS/iMessage webhook loop; the user-facing "harness" for the interview and human-in-the-loop approvals. |
| **Orchestration Engine** | **Simular Sai / Simulang** | Manages high-level state, intent classification, and multi-agent execution loops via stateful Hyperframes. |
| **Agent Observability** | **Arize AI** | Real-time execution tracing, latency monitoring, prompt debugging, cost tracking. |
| **Memory & Context Store** | **Redis** | Conversational state, session history, and intermediate JSON config / event-profile schema. |
| **Code & Deploy Generation** | **Claude Code / Opencode CLI** | Autonomous agentic coding via MCP — generates frontend code and pushes live to Vercel. |
| **Creative & Asset Pipeline** | **Midjourney & Pika** | Thematic branding: logos, color/UI tokens, background graphics; promo video snippets. |
| **Web Automation** | **Browserbase** | Headless browser to configure external platforms (Slack setup, Devpost init, forms). |
| **Cost Optimization** | **Token Compression (sponsor)** | Compresses long context (scrape context, deep interview history) before LLM calls. |
| **Deploy Target** | **Vercel** | Hosts the generated registration/marketing site. |

### 5.1 Architecture diagram

```
                        ┌─────────────────────────┐
                        │   Organizer (SMS only)  │
                        └────────────┬────────────┘
                                     │  text
                        ┌────────────▼────────────┐
                        │   Poke API (harness)    │  ◀── all human-in-loop
                        └────────────┬────────────┘      approvals pass here
                                     │  webhook
                        ┌────────────▼────────────┐
                        │  Simular Sai (dispatcher)│
                        │  intent · state · loops  │
                        └──┬─────────┬─────────┬───┘
              state R/W    │         │         │     traces
                 ┌─────────▼──┐      │     ┌───▼──────────┐
                 │   Redis    │      │     │   Arize AI   │
                 │  (memory)  │      │     │ (observ.)    │
                 └────────────┘      │     └──────────────┘
                                     │  on approval, fan out
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                             ▼
┌───────────────┐          ┌──────────────────┐          ┌────────────────┐
│ Midjourney /  │          │  Claude Code /   │          │  Browserbase   │
│ Pika          │  assets  │  Opencode CLI    │          │  (headless)    │
│ (brand assets)│ ───────▶ │  build + deploy  │          │ Slack/Devpost/ │
└───────────────┘          │  ──▶ Vercel      │          │ forms          │
                           └──────────────────┘          └────────────────┘
        └────────────────────────────┬────────────────────────────┘
                                     ▼
                     ┌───────────────────────────────┐
                     │ Final SMS: live URL + creds +  │
                     │ drafts for human to approve     │
                     └───────────────────────────────┘
```

---

## 6. Platform Flow (Detailed Recommendation)

> This section expands the team's high-level workflow into a **more specific, stage-by-stage flow**, with explicit attention to the *human-in-the-loop checkpoints* and *autonomy calibration* that are the product's core differentiator. **This is the recommended flow to build against.**

### Phase 0 — Initiation
1. Organizer texts a keyword (e.g. `PLAN`) to the Poke number.
2. Poke fires a webhook to the backend; Simular Sai creates a new **session** and an empty **Event Profile** record in Redis (keyed by phone number).
3. Sai sends a short welcome + sets expectations ("I'll ask ~8 quick questions, then show you a plan to approve.").

### Phase 1 — Conversational Interview (Poke → Sai → Redis)
The interview is a **dynamic branched state machine**, not a fixed form. Sai asks one thing at a time, adapts follow-ups, and writes each answer into the structured **Event Profile Schema** in Redis after every reply.

Fields to capture (recommended minimum set):
- **Identity:** event name, type (hackathon/conference/summit), date(s), location/virtual.
- **Scale:** expected attendees, team-vs-individual.
- **Budget:** total budget band + whether paid tools (domain, ads) are allowed.
- **Audience:** who it's for, how technical, geography.
- **Aesthetic:** vibe/theme, color preferences, any reference brands.
- **Operational needs:** Slack? Devpost? registration form fields? sponsors needed?
- **Sponsorship/marketing:** target sponsor list (if any), channels (email/social).

> **Recommendation:** Keep the interview to **6–10 questions max** for the demo. Use Sai's branching to skip irrelevant questions (e.g., don't ask about Devpost if it's a conference, not a hackathon). After the last question, echo a one-line "Got it, building your plan…" so the loop never feels dead.

### Phase 2 — Consensus Check-In (the first approval gate) ✋
1. Sai compiles the Event Profile into a **concise markdown summary** and texts it back.
2. **Execution pauses.** The system waits for an explicit reply:
   - `APPROVE` → proceed to Phase 3.
   - Any amendment text ("change the color to navy", "audience is undergrads only") → Sai patches the specific field in Redis, re-sends the updated summary, and waits again.
3. Nothing irreversible or costly has happened yet — this gate confirms the **plan**, not individual actions.

### Phase 3 — Calibrated Execution (the core of the build)
On approval, the orchestrator fans out. **Each task is tagged with an autonomy tier** (see §7). Tier-1 work runs automatically and in parallel; Tier-2/3 work queues for a human checkpoint.

**3a. Creative generation (Tier 1 — auto)**
- Midjourney generates logo, color/UI tokens, background graphics, all from a **single internal design-system seed** (locked aspect ratios + style suffixes) so outputs stay visually consistent.
- Pika generates an optional short promo clip.
- Assets are written to a shared directory the code agent will read from.

**3b. Site build + deploy (Tier 1 — auto)**
- Claude Code / Opencode CLI takes the Event Profile JSON **plus the generated assets**, builds a responsive single-page registration + marketing site (HTML/Tailwind), and pushes it live to Vercel.
- Site includes a working registration form wired to a simple store (e.g., a sheet/DB or form backend).

**3c. Platform automation (Tier 1 — auto, with graceful fallback)**
- Browserbase opens headless sessions to provision a **Slack workspace + standard channels**, and create a **Devpost draft**.
- If a third-party DOM breaks: catch the error, **don't fail the run** — write a clear manual fallback guide and continue.

**3d. Outreach compilation (Tier 3 — draft only, never auto-send)** ✋
- The system **drafts** sponsor outreach emails and a marketing sequence.
- It does **not send them** and does **not commit any spend**. These are queued for the human.

> **Latency UX recommendation:** the moment any long-running block starts, Poke sends a progress text ("🎨 Generating your branding — ~45s…", "🚀 Deploying your site…"). This keeps the SMS loop feeling alive and prevents perceived timeouts.

### Phase 4 — High-Stakes Handoff (the second approval gate) ✋
Before anything that touches **money or relationships**, Sai stops and presents it for explicit approval over SMS:
- "Here are 5 drafted sponsor emails. Reply `SEND` to send, `EDIT` to revise, or `SKIP`."
- "Buying the custom domain `xyz.com` costs $12. Reply `BUY` to confirm."

This is where autonomy is deliberately handed back to the human.

### Phase 5 — Final Delivery
Sai sends a single wrap-up text with:
- ✅ Live registration site URL (Vercel).
- ✅ Slack invite link + Devpost draft link.
- ✅ Brand asset folder link.
- ✅ Sponsor/marketing drafts (pending the human's send decision).
- ✅ Any fallback guides for steps that needed manual completion.

---

## 7. Autonomy Calibration Matrix (recommended)

The product's signature behavior is **calibrating autonomy to stakes**. Make it explicit and rule-based so it's demoable and trustworthy.

| Tier | Rule | Examples | Behavior |
|---|---|---|---|
| **Tier 1 — Auto** | Reversible, no money, no external relationships | Generate assets, build & deploy site, create Slack channels, draft Devpost | Run automatically, in parallel; just report results |
| **Tier 2 — Confirm plan** | Sets direction for downstream work | The full event profile summary | Pause once, get `APPROVE` / amendments |
| **Tier 3 — Human handoff** | Spends money OR contacts a real person/org OR mass-sends | Sponsor emails, paid ads, domain purchase, anything irreversible & external | Draft only; require explicit per-action approval before acting |

> **Why this matters for the pitch:** "It's not just an agent that does everything — it's an agent that *knows when not to*." This is the line that separates OrchestrateAI from a generic automation script.

---

## 8. Event Profile Schema (starting point)

```json
{
  "session_id": "phone:+1XXXXXXXXXX",
  "status": "interviewing | awaiting_approval | executing | awaiting_handoff | done",
  "event": {
    "name": "",
    "type": "hackathon | conference | summit",
    "dates": "",
    "location": "",
    "expected_attendees": 0,
    "format": "in_person | virtual | hybrid"
  },
  "budget": { "total_usd": 0, "paid_tools_allowed": false },
  "audience": { "description": "", "technical_level": "", "geography": "" },
  "aesthetic": { "vibe": "", "colors": [], "references": [] },
  "ops": { "needs_slack": true, "needs_devpost": true, "registration_fields": [] },
  "outreach": { "sponsor_targets": [], "channels": [] },
  "artifacts": {
    "asset_urls": [], "site_url": "", "slack_url": "",
    "devpost_url": "", "outreach_drafts": []
  },
  "approvals": { "plan_approved": false, "handoff_decisions": [] }
}
```

---

## 9. Implementation Roadmap (24–48h hackathon)

### Milestone 1 — Core harness & stateful loop (Hours 0–12)
- **1.1** Stand up the Poke SMS webhook server → forward payloads to Express/Python backend.
- **1.2** Implement Simular Sai with dynamic Hyperframes; deterministic state machine for the intake interview.
- **1.3** Connect Redis to persist the state dict across async SMS exchanges.
- **1.4** Initialize Arize tracking hooks across all LLM nodes to catch prompt failures early.

### Milestone 2 — Tool integration & code automation (Hours 12–24)
- **2.1** Script the Claude Code / Opencode CLI pipeline: JSON event schema → clean HTML/Tailwind landing page.
- **2.2** Configure Browserbase: robust script to log into a mock platform (form builder / fresh Slack) to verify headless nav.
- **2.3** Wire Midjourney + Pika to trigger programmatically from extracted aesthetic descriptions.

### Milestone 3 — End-to-end orchestration & polish (Hours 24–36)
- **3.1** Implement the check-in/approval checkpoint logic; execution halts until Poke gets the affirmative.
- **3.2** Connect output branches so Midjourney assets feed automatically into the directory Claude Code compiles from.
- **3.3** Inject Token Compression around prompt-history loops to optimize time + context windows.

### Milestone 4 — Validation & pitch prep (Hours 36–48)
- **4.1** Run a full end-to-end Arize trace: cost, token efficiency, bottlenecks.
- **4.2** Record a clean walkthrough: blank slate → initial text → live Vercel generation → deployed setup.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Headless automation breaks** on dynamic third-party DOMs during live judging | Scope Browserbase to clean/stable steps (standard Slack wizard). On failure, degrade gracefully: catch error, write a fallback guide for the human, continue to code-gen. |
| **High generation latency** times out / deadens the SMS loop | Immediate confirmation dispatches via Poke ("Processing visuals, ~45s…") on entering every long-running block. |
| **Fragmented visual aesthetics** from decoupled image generators | Pass strict system-defined seeds, exact aspect ratios, explicit style suffixes (`--style raw`, font tokens) from one internal design system — not loose user text. |
| **Agent over-reaches** (sends emails / spends money) | Enforce the §7 autonomy matrix in the orchestrator: Tier-3 actions are draft-only until explicit per-action SMS approval. |
| **State loss / dropped dependency** | Redis is the single source of truth; every interview answer and artifact URL is persisted immediately, keyed by session. |

---

## 11. Success Metrics (demo)

- **Time-to-deployed-event:** blank slate → live site < ~1 hour in the demo.
- **Single-thread completion:** entire flow completable over SMS with zero dashboard use.
- **Approval gates fire correctly:** plan gate + at least one Tier-3 handoff gate demonstrated.
- **Graceful degradation:** at least one simulated third-party failure handled without crashing the run.
- **Observability:** a clean Arize trace showing cost + latency per node.

---

## 12. Open Questions for the Team

1. What's the registration form backend (Vercel form / Google Sheet / lightweight DB)?
2. Slack provisioning — real workspace via Browserbase, or a pre-created workspace we configure?
3. Domain strategy for the demo — Vercel default subdomain, or a real purchased domain (Tier-3 spend)?
4. How much of the sponsor-email content is generated vs. templated for the demo?
5. Fallback owner — when a Tier-1 automation fails, does the run continue silently or notify the organizer mid-run?
```
