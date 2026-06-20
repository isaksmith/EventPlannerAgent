# Event Planner Agent Hackathon Project Specification & Implementation Plan

Repository: https://github.com/isaksmith/EventPlannerAgent.git

## Project Name

**OrchestrateAI** (Working Title)

## Target Event

UC Berkeley AI Hackathon 2026

## Objective

A stateful, multi-agent event planning orchestration engine that transforms a conversational SMS interview into a fully deployed, cross-platform large-scale hackathon or major event in a matter of hours.

## 1. Executive Summary & Vision

Planning massive events requires severe overhead across fragmented verticals (web development, marketing, platform setup, sponsor management). This project replaces weeks of human coordination with an autonomous agent network. By interfacing primarily through a simple SMS chat, the system interviews the organizer, builds a comprehensive event profile, and sequentially executes tasks ranging from asset generation to full web deployment and platform configuration.

## 2. System Architecture & Integration Matrix

The platform relies on a decoupled, event-driven multi-agent architecture where Simular Sai acts as the central cognitive dispatcher, routing sub-tasks to specialized micro-agents and tools.

| Component / Layer | Technology | Functional Responsibility |
| --- | --- | --- |
| Inbound Interface | Poke API | Handles SMS/iMessage webhook loop; acts as the user-facing harness for the initial interview and human-in-the-loop approvals. |
| Orchestration Engine | Simular Sai / Simulang | Manages high-level state, intent classification, and multi-agent execution loops using stateful Hyperframes. |
| Agent Observability | Arize AI | Provides real-time execution tracing, latency monitoring, prompt debugging, and cost tracking. |
| Memory & Context Store | Redis | Maintains conversational state, session histories, and intermediate JSON configuration state schemas. |
| Code & Deployment Generation | Claude Code / Opencode CLI | Autonomous agentic coding block via Model Context Protocol (MCP) to generate frontend code and instantly push to Vercel. |
| Creative & Asset Pipeline | Midjourney & Pika | Generates thematic visual branding assets, logos, background UI graphic tokens, and promotional video assets. |
| Web Automation & Execution | Browserbase | Provides headless browser execution environment to automate configurations on external platforms (e.g., Slack setup, Devpost initialization). |
| Cost Optimization | Token Compression Sponsor | Compresses long context vectors (e.g., rich scraping context or deep interview history) before sending to LLM APIs. |

## 3. Core Workflow Engine

```text
[ User Texts Poke Harness ]
         │
         ▼
[ Simular Sai Interactive Interview Loop ] ──>(Saves State to Redis)
         │
         ▼
[ Human-in-the-Loop Check-In Summary ] ──>(Approved via SMS reply)
         │
         ├──> [ Midjourney/Pika Asset Pipeline ]
         ├──> [ Claude Code / Opencode CLI ] ──> Deploys Web App to Vercel
         └──> [ Browserbase Automation ] ──────> Sets up Devpost/Slack/Forms
         │
         ▼
[ Final Event Dashboard URL & Credentials Delivered via SMS ]
```

### Phase 1: The Inbound Interview (Poke ➔ Sai ➔ Redis)

- The user texts a keyword to the Poke SMS number to initialize the workflow.
- Simular Sai initiates a dynamically branched intake interview to gather critical parameters: event name, budget constraints, target audience, aesthetic themes, and operational needs.
- Every response is structured dynamically into a centralized Event Profile Schema stored in Redis.

### Phase 2: The Consensus Check-In

- Once the engine builds a complete operational matrix, it sends a highly concise markdown summary back to the user via SMS.
- The system pauses execution, waiting for an explicit `Approve` or specific amendment text from the user (Human-in-the-Loop constraint).

### Phase 3: Parallel Execution Blocks

Upon approval, the orchestrator splits into three primary concurrent execution vectors:

- **Creative Generation:** Midjourney generates UI design tokens, color schemes, and high-fidelity logos based on the interview themes. Pika animates brand promotional snippets.
- **Autonomous Code Base:** Claude Code parses the visual design layouts, combines them with the data schema, builds a responsive single-page marketing and registration platform, and pushes it live to Vercel.
- **Platform Automation:** Browserbase opens secure, headless instances to navigate to administrative portals. It programmatically provisions a community Slack workspace, establishes standard channels, builds a Devpost submission draft, and compiles sponsor outreach email sequences.

## 4. 24-to-48 Hour Hackathon Implementation Roadmap

### Milestone 1: Core Harness & Stateful Loop (Hours 0–12)

- **Task 1.1:** Stand up the Poke SMS webhook server to ingest incoming messages and forward payloads to an Express/Python backend.
- **Task 1.2:** Implement the Simular Sai framework using dynamic Hyperframes. Create a deterministic state machine for the intake interview.
- **Task 1.3:** Connect Redis to store the state dictionary so the model maintains context across distinct asynchronous SMS exchanges.
- **Task 1.4:** Initialize Arize tracking hooks across all LLM interaction nodes to immediately identify prompt failures.

### Milestone 2: Tool Integration & Code Automation (Hours 12–24)

- **Task 2.1:** Script the Claude Code / Opencode CLI pipeline. Build an MCP script that can take a raw JSON event schema and output a clean, modern HTML/Tailwind landing page template.
- **Task 2.2:** Configure Browserbase API integration. Write a robust browser script to log into a mock platform (e.g., a form builder or a fresh Slack workspace setup) to verify headless navigation capabilities.
- **Task 2.3:** Wire the Midjourney and Pika generation APIs to trigger programmatically based on the extracted aesthetic descriptions from Phase 1.

### Milestone 3: End-to-End Orchestration & Polish (Hours 24–36)

- **Task 3.1:** Implement the check-in / approval checkpoint logic in the central orchestrator. Ensure execution safely halts until Poke receives the affirmative response.
- **Task 3.2:** Connect the output branches so asset files from Midjourney are fed automatically into the directory structure that Claude Code compiles.
- **Task 3.3:** Inject the token compression engine wrapper around the prompt history loops to optimize execution time and context windows.

### Milestone 4: Validation & Pitch Prep (Hours 36–48)

- **Task 4.1:** Run a complete end-to-end trace inside Arize to measure costs, token efficiency, and isolate execution bottlenecks.
- **Task 4.2:** Record a pristine walkthrough demo starting with a blank slate, sending the initial text, showing the live Vercel generation, and concluding with a deployed hackathon setup.

## 5. High-Risk Vulnerabilities & Mitigation Strategies

### Vulnerability: Headless browser automation breaking due to dynamic DOM adjustments on third-party platforms during live judging

**Mitigation:** Keep the Browserbase scope focused on clean, API-accessible steps or platforms with stable DOM elements (like standard Slack setup wizards). Ensure graceful degradation—if a third-party setup fails, catch the error, write a detailed fallback guide for the human planner, and move directly to the code generation phase.

### Vulnerability: High generation latency causing the Poke SMS loop to time out or feel unresponsive to the user

**Mitigation:** Use immediate confirmation text dispatches (e.g., "Processing your visual assets, this will take roughly 45 seconds...") via Poke immediately upon entering a long-running execution block to preserve interactive consistency.

### Vulnerability: Fragmented visual aesthetics caused by decoupled image generators

**Mitigation:** Pass strict, system-defined seed descriptions, exact aspect ratios, and explicit style parameter suffixes (for example, `--style raw` or specific font tokens) down to the Midjourney pipeline based on a clean internal design system template rather than relying completely on loose, unguided user text inputs.

## Summary

OrchestrateAI is designed as a stateful, autonomous event operations engine that turns a lightweight SMS conversation into a production-ready event presence and operations stack. The architecture emphasizes modular orchestration, human approval checkpoints, and parallel execution across creative, engineering, and platform automation workflows.
