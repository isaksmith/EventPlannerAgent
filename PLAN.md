# OrchestrateAI — Implementation Plan

> **Source of truth:** [`spec.md`](./spec.md) (tech spec) · cross-referenced with [`PRD.md`](./PRD.md) and [`docs/superpowers/specs/2026-06-20-orchestrateai-mock-prototype-design.md`](./docs/superpowers/specs/2026-06-20-orchestrateai-mock-prototype-design.md)
> **Target event:** UC Berkeley AI Hackathon 2026
> **Status:** Planning — maps every component in spec.md §2 (Integration Matrix) and §4 (Roadmap) to concrete build tasks, owners, and seams.

---

## 0. Current State

| Artifact | Status |
|---|---|
| `spec.md` | ✅ Tech spec — the system to build |
| `PRD.md` | ✅ Product requirements (phases, autonomy tiers, schema) |
| Mock prototype design doc | ✅ Approved front-end-only visual skeleton |
| `index.html` | 🟡 Mock prototype exists (~523 lines, desktop-platform variant). **Not** the real system. |
| Real backend / integrations | ❌ None yet |

**Key clarification:** `spec.md` describes the **real** stateful multi-agent system. The mock `index.html` is a separate visual reference. This plan implements the **real** system from spec.md, using the mock panels as the visual contract for each integration seam.

---

## 1. Architecture Recap (spec.md §2)

Decoupled, event-driven, multi-agent. **Simular Sai** = central cognitive dispatcher. State in **Redis**. Inbound via **Poke API** (SMS). Observability via **Arize**. Three parallel execution vectors on approval: Creative (Midjourney/Pika), Code+Deploy (Claude Code/Opencode → Vercel), Platform Automation (Browserbase). Token Compression wraps long contexts.

```
SMS → Poke → Sai (dispatcher) ⇄ Redis (state) → Arize (trace)
                       │  on APPROVE, fan out
        ┌──────────────┼──────────────────────┐
   Midjourney/Pika  Claude Code→Vercel   Browserbase
   (assets)         (site build+deploy)  (Slack/Devpost/forms)
                       │
              Final SMS: URL + creds + drafts
```

---

## 2. Repository / Project Structure (proposed)

```
EventPlannerAgent/
├── spec.md, PRD.md, PLAN.md            # docs
├── index.html                          # mock prototype (keep as visual ref)
├── backend/                            # orchestration backend (NEW)
│   ├── pyproject.toml                  # python (FastAPI) — chosen for Sai/Arize SDK fit
│   ├── app/
│   │   ├── main.py                     # FastAPI app, webhook routes
│   │   ├── webhooks/poke.py            # Poke SMS webhook handler
│   │   ├── orchestrator/
│   │   │   ├── sai.py                   # Simular Sai dispatcher + Hyperframes
│   │   │   ├── state_machine.py         # interview state machine (Phase 1)
│   │   │   ├── approval_gate.py         # Phase 2 + Phase 4 gates
│   │   │   └── executor.py              # Phase 3 fan-out + Tier routing
│   │   ├── memory/
│   │   │   ├── redis_store.py           # session + Event Profile CRUD
│   │   │   └── schema.py                # Event Profile schema (PRD §8)
│   │   ├── integrations/
│   │   │   ├── poke.py                  # outbound SMS send
│   │   │   ├── midjourney.py, pika.py   # creative pipeline
│   │   │   ├── claude_code.py           # MCP codegen → Vercel deploy
│   │   │   ├── browserbase.py           # headless Slack/Devpost/forms
│   │   │   ├── outreach.py              # Tier-3 draft-only email gen
│   │   │   └── token_compression.py     # context compression wrapper
│   │   ├── observability/arize.py       # tracing hooks on every LLM node
│   │   └── config.py                    # env, keys, tier rules
│   ├── tests/
│   └── docker-compose.yml               # redis + backend for local dev
└── docs/
```

**Stack decision:** Python + FastAPI. Rationale: Simular Sai + Arize have Python-first SDKs; async webhook handling is trivial; matches spec.md §4 Task 1.1 ("Express/Python backend").

---

## 3. Component Build Plan (maps to spec.md §2 Integration Matrix)

Each component below = one integration seam. Owner swaps mock → real.

### 3.1 Inbound Interface — Poke API  *(spec §2 row 1, §4 Task 1.1)*
- [ ] Provision Poke number; capture webhook signing secret + outbound send API.
- [ ] `webhooks/poke.py`: verify signature, parse inbound SMS, route to Sai dispatcher keyed by phone number.
- [ ] `integrations/poke.py`: `send_sms(to, body)` helper used for all outbound (welcome, progress, summaries, gates, final delivery).
- [ ] Latency-UX: emit progress texts on entering any long-running block (spec §5 mitigation).
- **Seam:** replaces the mock "Phone SMS I/O" panel.

### 3.2 Orchestration Engine — Simular Sai / Simulang  *(spec §2 row 2, §4 Task 1.2)*
- [ ] `orchestrator/sai.py`: Sai client init; intent classification on each inbound message.
- [ ] `state_machine.py`: deterministic branched interview state machine (Phase 1) — 6–10 questions, branching skips irrelevant ones (PRD §6 Phase 1).
- [ ] `approval_gate.py`: Phase 2 consensus gate (APPROVE / amend) + Phase 4 high-stakes gate (SEND/EDIT/SKIP/BUY). Execution halts until reply.
- [ ] `executor.py`: Phase 3 fan-out — dispatch Tier-1 tasks in parallel, queue Tier-3 as draft-only.
- [ ] Hyperframes: model each phase as a stateful Hyperframe; persist frame id in Redis.
- **Seam:** replaces `mockSai`.

### 3.3 Memory & Context Store — Redis  *(spec §2 row 4, §4 Task 1.3)*
- [ ] `docker-compose.yml`: local Redis.
- [ ] `memory/redis_store.py`: session CRUD keyed by `phone:+1...`; atomic writes per interview answer.
- [ ] `memory/schema.py`: Event Profile schema (PRD §8) as typed model; status field drives phase transitions.
- [ ] Persist every artifact URL + approval decision immediately (spec §10 "state loss" mitigation).
- **Seam:** replaces `mockRedis`.

### 3.4 Agent Observability — Arize AI  *(spec §2 row 3, §4 Task 1.4)*
- [ ] `observability/arize.py`: tracing wrapper around every LLM call and every integration call.
- [ ] Spans: node name, latency ms, token count, cost. Surface in a live trace view.
- [ ] Hook all nodes before Milestone 2 so failures surface early.
- **Seam:** replaces `mockArize`.

### 3.5 Code & Deploy Generation — Claude Code / Opencode CLI  *(spec §2 row 5, §4 Task 2.1, §3.2)*
- [ ] `integrations/claude_code.py`: MCP script — input = Event Profile JSON + generated asset URLs → output = HTML/Tailwind single-page registration + marketing site.
- [ ] Wire registration form to a backend store (resolve PRD §12 Q1 — recommend Vercel form / simple KV).
- [ ] Deploy to Vercel via Vercel API; capture live URL into Redis `artifacts.site_url`.
- [ ] Feed Midjourney assets into the build directory automatically (spec §4 Task 3.2).
- **Seam:** replaces `mockClaudeCode`.

### 3.6 Creative & Asset Pipeline — Midjourney & Pika  *(spec §2 row 6, §4 Task 2.3, §3.1)*
- [ ] `integrations/midjourney.py`: generate logo, color/UI tokens, bg graphics from a **single internal design-system seed** (locked aspect ratios + `--style raw` suffixes) — spec §5 mitigation.
- [ ] `integrations/pika.py`: short promo clip from extracted aesthetic.
- [ ] Write assets to shared directory Claude Code reads from.
- **Seam:** replaces `mockMidjourney` / `mockPika`.

### 3.7 Web Automation — Browserbase  *(spec §2 row 7, §4 Task 2.2, §3.3)*
- [ ] `integrations/browserbase.py`: headless sessions to provision Slack workspace + standard channels, create Devpost draft.
- [ ] Scope to stable DOM steps (standard Slack wizard) — spec §5 mitigation.
- [ ] Graceful degradation: on failure, catch, write manual fallback guide to Redis, continue run (do not crash).
- **Seam:** replaces `mockBrowserbase`.

### 3.8 Outreach Compilation — Tier-3 draft-only  *(spec §3.4, §7 Tier 3)*
- [ ] `integrations/outreach.py`: draft sponsor emails + marketing sequence from Event Profile.
- [ ] **Never auto-send.** Queue for Phase 4 human gate; require explicit per-action SMS approval.
- **Seam:** replaces `mockOutreach`.

### 3.9 Cost Optimization — Token Compression  *(spec §2 row 8, §4 Task 3.3)*
- [ ] `integrations/token_compression.py`: wrapper around prompt-history loops; compress long context (scrape context, deep interview history) before LLM calls.
- [ ] Apply to interview history + any scraped context fed to Sai/Claude Code.
- **Seam:** wraps existing LLM calls (no mock panel).

---

## 4. Phase-by-Phase Flow Implementation (spec.md §3, PRD §6)

| Phase | Build tasks | Gate? |
|---|---|---|
| **0 — Initiation** | `PLAN` keyword → new session + empty Event Profile in Redis; welcome text. | — |
| **1 — Interview** | Branched state machine; each answer → Redis field write; "building your plan" echo. | — |
| **2 — Consensus** | Compile profile → markdown summary SMS; halt for APPROVE/amend. | ✋ Tier 2 |
| **3 — Calibrated execution** | Fan-out: Creative (T1) → Code+Deploy (T1) → Browserbase (T1, graceful fail) → Outreach drafts (T3). Progress texts on each. | — |
| **4 — High-stakes handoff** | Present Tier-3 drafts/spend; halt for SEND/EDIT/SKIP/BUY. | ✋ Tier 3 |
| **5 — Final delivery** | Single wrap-up SMS: site URL + Slack + Devpost + asset folder + pending drafts + fallback guides. | — |

**Autonomy calibration (spec §7 / PRD §7):** enforce Tier rules in `executor.py` — Tier-1 auto/parallel, Tier-2 plan-confirm, Tier-3 draft-only until per-action approval. This is the pitch differentiator.

---

## 5. Milestone Roadmap (spec.md §4 — 24–48h)

### Milestone 1 — Core harness & stateful loop (Hours 0–12)
- [ ] 1.1 Poke SMS webhook server → FastAPI backend
- [ ] 1.2 Sai + Hyperframes; deterministic interview state machine
- [ ] 1.3 Redis persistence across async SMS exchanges
- [ ] 1.4 Arize hooks on all LLM nodes

### Milestone 2 — Tool integration & code automation (Hours 12–24)
- [ ] 2.1 Claude Code/Opencode MCP pipeline: JSON schema → HTML/Tailwind landing page
- [ ] 2.2 Browserbase: headless login on mock platform to verify nav
- [ ] 2.3 Midjourney + Pika wired to trigger from aesthetic descriptions

### Milestone 3 — End-to-end orchestration & polish (Hours 24–36)
- [ ] 3.1 Approval checkpoint logic; execution halts until Poke affirmative
- [ ] 3.2 Connect asset → code-build directory pipeline
- [ ] 3.3 Token Compression wrapper around prompt-history loops

### Milestone 4 — Validation & pitch prep (Hours 36–48)
- [ ] 4.1 Full end-to-end Arize trace: cost, token efficiency, bottlenecks
- [ ] 4.2 Walkthrough recording: blank slate → text → live Vercel gen → deployed setup

---

## 6. Risk Mitigations (spec.md §5)

| Risk | Mitigation (build into code) |
|---|---|
| Headless automation breaks on dynamic DOM | Scope Browserbase to stable steps; try/catch → fallback guide → continue. |
| High latency deadens SMS loop | Progress text dispatch on entering every long-running block. |
| Fragmented visual aesthetics | Single design-system seed; locked aspect ratios + style suffixes. |
| Agent over-reaches (sends/spends) | Tier matrix enforced in `executor.py`; Tier-3 = draft-only until per-action SMS approval. |
| State loss / dropped dependency | Redis = single source of truth; immediate persist of every answer + artifact URL. |

---

## 7. Open Questions (PRD §12 — need team decisions before/during build)

1. Registration form backend? (recommend Vercel form / KV for demo)
2. Slack provisioning — real workspace via Browserbase, or pre-created workspace we configure?
3. Domain strategy — Vercel subdomain (T1) or real purchased domain (T3 spend)?
4. Sponsor emails — generated vs templated for demo?
5. Fallback owner — on Tier-1 failure, continue silently or notify organizer mid-run?

---

## 8. Definition of Done (spec.md success metrics, PRD §11)

- [ ] Time-to-deployed-event: blank slate → live site < ~1 hour in demo.
- [ ] Entire flow completable over SMS, zero dashboard.
- [ ] Both approval gates fire correctly (Phase 2 plan + Phase 3 Tier-3 handoff).
- [ ] At least one simulated third-party failure handled gracefully (no crash).
- [ ] Clean Arize trace showing cost + latency per node.
