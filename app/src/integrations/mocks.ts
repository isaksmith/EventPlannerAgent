// ============================================================================
// MOCK IMPLEMENTATIONS of the integration contracts.  EVERYTHING HERE IS FAKE.
// ----------------------------------------------------------------------------
// These satisfy the interfaces in ./contracts.ts with canned data and tiny
// delays so the demo feels real. To go live, write real implementations of the
// same interfaces and swap them in ./index.ts. Search for // TODO[teammate].
// ============================================================================
import type {
  Integrations, SaiAgent, MemoryStore, BrandService, DeployService,
  BrowserbaseService, OutreachService, Tracer,
} from './contracts'
import type { EventProfile, ArizeSpan } from '../types'

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

function emptyProfile(): EventProfile {
  return {
    session_id: 'session:demo-001', status: 'interviewing',
    event: {}, audience: {}, aesthetic: {}, ops: {}, outreach: {}, artifacts: {},
  }
}
function setDeep(obj: Record<string, any>, path: string, value: unknown) {
  const keys = path.split('.')
  let cur = obj
  for (let i = 0; i < keys.length - 1; i++) cur = cur[keys[i]] ??= {}
  cur[keys[keys.length - 1]] = value
}

// TODO[teammate · Simular Sai]: replace with real intent + Hyperframe routing.
const sai: SaiAgent = {
  async classifyIntent(text) {
    await wait(80)
    return /plan|event/i.test(text) ? 'START_PLAN' : 'INTERVIEW_REPLY'
  },
}

// TODO[teammate · Redis]: replace with a real session store keyed by session id.
function createMemory(): MemoryStore {
  const profile = emptyProfile()
  return {
    async set(path, value) { await wait(20); setDeep(profile, path, value) },
    async getProfile() { return JSON.parse(JSON.stringify(profile)) },
  }
}

// TODO[teammate · Midjourney]: replace with real async brand-asset generation.
const brand: BrandService = {
  async generateBrandKit() {
    await wait(200)
    return {
      vibe: 'retro-futuristic · navy/cyan',
      logo: { text: 'B/AI', accent: '#8B5CF6', bg: '#0A1F44' },
      palette: [
        { hex: '#0A1F44', name: 'Midnight Navy' },
        { hex: '#22D3EE', name: 'Neon Cyan' },
        { hex: '#8B5CF6', name: 'Signal Violet' },
        { hex: '#0E1B2E', name: 'Deep Space' },
      ],
      assets: [
        { label: 'Hero image', glyph: '◢◤' }, { label: 'Pattern', glyph: '▦▦' },
        { label: 'Background', glyph: '◢◤' }, { label: 'Social card', glyph: '▤' },
        { label: 'Brand motion · 6s', glyph: '▶' }, { label: 'Banner', glyph: '▭' },
      ],
    }
  },
}

// TODO[teammate · Claude Code / Opencode → Vercel]: real codegen + deploy.
const deploy: DeployService = {
  async buildAndDeploy() {
    await wait(200)
    return {
      url: 'berkeley-ai-hack.vercel.app',
      eyebrow: 'UC BERKELEY · 2026',
      title: 'Berkeley AI Hackathon',
      subtitle: '200 builders · 6 weeks out · in person',
    }
  },
}

// TODO[teammate · Browserbase]: real headless provisioning. Never throw — on
// failure return { ok: false, fallback }. The UI relies on that contract.
const browserbase: BrowserbaseService = {
  async provisionSlack() {
    await wait(150)
    return { ok: true, channels: ['#general', '#help-desk', '#team-formation', '#sponsors', '#announcements'] }
  },
  async createDevpost() {
    await wait(120)
    return { ok: false, fallback: 'Devpost wizard DOM changed — manual guide written' }
  },
}

// TODO[teammate · drafting]: real draft generation. MUST stay draft-only.
const outreach: OutreachService = {
  async draftSponsorEmails() {
    await wait(150)
    return [
      { to: 'partnerships@anthropic.com', subject: 'Anthropic × Berkeley AI Hackathon 2026', body: "Hi Anthropic team,\n\nWe're hosting 200 student builders at UC Berkeley in 6 weeks and would love Anthropic as a headline sponsor — API credits + a workshop slot. Quick call this week?\n\nThanks,\nMichael" },
      { to: 'devrel@openai.com', subject: 'Sponsor 200 builders at UC Berkeley', body: "Hi OpenAI DevRel,\n\nBerkeley AI Hackathon 2026 — 200 undergrad & grad builders, in person. Would you sponsor credits and send a mentor? Happy to share the prospectus.\n\nBest,\nMichael" },
      { to: 'community@vercel.com', subject: 'Vercel as deploy partner — Berkeley AI Hack', body: "Hi Vercel community team,\n\nWe're deploying every hack on Vercel and would love you as our official deploy partner — swag + Pro credits for participants. Interested?\n\nCheers,\nMichael" },
    ]
  },
}

// TODO[teammate · Arize]: forward spans to Arize. Returning the span lets the
// "Behind the scenes" trace render it; real Arize would also ship it onward.
const tracer: Tracer = {
  span(node, ms, cost, warn): ArizeSpan { return { node, ms, cost, warn } },
}

export function createMockIntegrations(): Integrations {
  return { sai, memory: createMemory(), brand, deploy, browserbase, outreach, tracer }
}
