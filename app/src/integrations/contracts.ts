// ============================================================================
// INTEGRATION CONTRACTS  —  THE SEAM YOUR TEAM IMPLEMENTS.
// ----------------------------------------------------------------------------
// Each interface below is the boundary between Marquee's UI and a real service.
// The UI only ever talks to these interfaces. To go live, implement them with
// real backends (see ./mocks.ts for the shapes) and swap them in ./index.ts —
// no UI changes required. Everything is async on purpose: real calls are I/O.
// ============================================================================
import type {
  EventProfile, BrandKit, SiteResult, SlackResult, DevpostResult, EmailDraft, ArizeSpan,
} from '../types'

/** Simular Sai — intent + orchestration brain. (Owns the conversation in prod.) */
export interface SaiAgent {
  classifyIntent(text: string): Promise<'START_PLAN' | 'INTERVIEW_REPLY'>
}

/** Redis — persistent event-profile / session store, keyed by session id. */
export interface MemoryStore {
  set(path: string, value: unknown): Promise<void>
  getProfile(): Promise<EventProfile>
}

/** Midjourney — generates the full brand kit (logo, palette, images, motion). */
export interface BrandService {
  generateBrandKit(profile: EventProfile): Promise<BrandKit>
}

/** Claude Code / Opencode → Vercel — builds & deploys the registration site. */
export interface DeployService {
  buildAndDeploy(profile: EventProfile, brand: BrandKit): Promise<SiteResult>
}

/** Browserbase — headless provisioning. MUST degrade gracefully (never throw). */
export interface BrowserbaseService {
  provisionSlack(profile: EventProfile): Promise<SlackResult>
  createDevpost(profile: EventProfile): Promise<DevpostResult>
}

/** Drafting — sponsor outreach. MUST stay draft-only (never auto-send). */
export interface OutreachService {
  draftSponsorEmails(profile: EventProfile): Promise<EmailDraft[]>
}

/** Arize — observability. Records a span; returns it for the live trace view. */
export interface Tracer {
  span(node: string, ms: number, cost: number, warn?: boolean): ArizeSpan
}

/** The full set of services the orchestrator depends on. Implement & wire all. */
export interface Integrations {
  sai: SaiAgent
  memory: MemoryStore
  brand: BrandService
  deploy: DeployService
  browserbase: BrowserbaseService
  outreach: OutreachService
  tracer: Tracer
}
