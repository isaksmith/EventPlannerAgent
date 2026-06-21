// ============================================================================
// DEMO SCRIPT — the canned timeline that drives this prototype.
// ----------------------------------------------------------------------------
// This is the "fake engine". It plays one scripted event end-to-end. In the
// real product you'd REPLACE this with a live loop where Sai drives the
// conversation dynamically and calls the integrations (see useOrchestrator.ts).
// Each step declares what changes; the runner applies whichever fields exist.
// `produce` triggers a real (mocked) integration call + reveals its tile.
// ============================================================================
import type { Phase, ChatAction, ArizeSpan, ProfileStatus } from '../types'

export const PHASES = ['Initiation', 'Interview', 'Consensus', 'Execution', 'Handoff', 'Delivery'] as const
export const STATUS = [
  'Getting started', 'Learning about your event', 'Confirming the plan',
  'Building your event', 'Needs your approval', 'All set 🎉',
] as const

export type Produce = 'branding' | 'website' | 'slack' | 'devpost' | 'outreach'

export interface Step {
  phase?: Phase
  tier?: 1 | 2 | 3
  sai?: { stat?: 'active' | 'done'; intent?: string; node?: string; log?: string }
  status?: ProfileStatus
  write?: [string, unknown][]
  span?: ArizeSpan
  produce?: Produce
  msg?: { from: 'sai' | 'user'; text: string; actions?: ChatAction[] }
}

export const demoScript: Step[] = [
  // PHASE 0 — Initiation
  { phase: 0, msg: { from: 'user', text: 'I want to plan an event' } },
  { phase: 0, sai: { stat: 'active', intent: 'START_PLAN', node: 'session.create', log: 'new session → session:demo-001' }, span: { node: 'intent.classify', ms: 180, cost: 0.0009 } },
  { phase: 0, msg: { from: 'sai', text: "Hi — I'm Marquee, your event planner. I'll ask a few quick questions, then build it all for you. Ready?" } },

  // PHASE 1 — Interview
  { phase: 1, sai: { node: 'interview.identity', log: 'branch → identity' }, msg: { from: 'sai', text: 'First — what are we building? (name + type)' } },
  { phase: 1, msg: { from: 'user', text: 'Berkeley AI Hackathon 2026, a hackathon' } },
  { phase: 1, write: [['event.name', 'Berkeley AI Hackathon 2026'], ['event.type', 'hackathon']], span: { node: 'interview.branch', ms: 240, cost: 0.0011 } },
  { phase: 1, sai: { node: 'interview.scale' }, msg: { from: 'sai', text: 'Nice. When & where, and how many people?' } },
  { phase: 1, msg: { from: 'user', text: 'UC Berkeley, in person, 6 weeks out, ~200 attendees' } },
  { phase: 1, write: [['event.location', 'UC Berkeley · in person'], ['event.expected_attendees', 200]] },
  { phase: 1, sai: { node: 'interview.aesthetic' }, msg: { from: 'sai', text: "Who's it for, and what's the vibe / colors?" } },
  { phase: 1, msg: { from: 'user', text: 'Undergrad + grad builders. Retro-futuristic, deep navy + neon cyan' } },
  { phase: 1, write: [['audience.description', 'undergrad + grad builders'], ['aesthetic.vibe', 'retro-futuristic · navy/cyan']], span: { node: 'interview.branch', ms: 210, cost: 0.0010 } },
  { phase: 1, sai: { node: 'interview.ops' }, msg: { from: 'sai', text: 'Want a Slack + Devpost, and any sponsors to reach out to?' } },
  { phase: 1, msg: { from: 'user', text: 'Yes Slack + Devpost. Sponsors: Anthropic, OpenAI, Vercel' } },
  { phase: 1, write: [['ops.needs_slack', true], ['ops.needs_devpost', true], ['outreach.sponsor_targets', ['Anthropic', 'OpenAI', 'Vercel']]] },
  { phase: 1, sai: { stat: 'active', node: 'summary.compile', log: 'compiling event profile' }, span: { node: 'summary.compile', ms: 520, cost: 0.0024 }, msg: { from: 'sai', text: 'Perfect — putting your plan together…' } },

  // PHASE 2 — Consensus gate
  { phase: 2, tier: 2, status: 'awaiting_approval', msg: { from: 'sai', text: "Here's the plan:\n\nBerkeley AI Hackathon 2026 (hackathon)\nUC Berkeley · in person · ~200 people · 6 weeks out\nLook: retro-futuristic · navy/cyan\nSlack + Devpost\nReach out to: Anthropic, OpenAI, Vercel\n\nApprove and I'll build everything." } },
  { phase: 2, sai: { node: 'gate.plan', log: 'paused — awaiting plan approval' }, msg: { from: 'sai', text: 'Sound right?', actions: [
    { label: 'Approve — build it', kind: 'primary', reply: 'Approve' },
    { label: 'Change the colors', kind: 'line', reply: 'actually, navy only' },
  ] } },
  { phase: 3, status: 'executing', sai: { stat: 'active', node: 'fanout', log: 'plan approved → fan out' }, msg: { from: 'sai', text: "On it! I'll build everything now and show you each piece as it's ready. Sit tight." } },

  // PHASE 3 — Calibrated execution (tiles appear as each finishes)
  { phase: 3, tier: 1, sai: { node: 'exec.creative', log: 'Midjourney jobs queued (logo, palette, images, background, motion)' }, span: { node: 'midjourney.logo', ms: 4200, cost: 0.0180 }, msg: { from: 'sai', text: 'Designing your brand identity…' } },
  { phase: 3, produce: 'branding', span: { node: 'midjourney.assets', ms: 3600, cost: 0.0190 }, msg: { from: 'sai', text: 'Your brand is ready — logo, colors, images and a background. Opened it on the right. 🎨 Tap “Maximize” to see everything.' } },

  { phase: 3, tier: 1, sai: { node: 'exec.deploy', log: 'Claude Code: profile + assets → site → Vercel' }, span: { node: 'claude.build', ms: 6800, cost: 0.0410 }, msg: { from: 'sai', text: 'Now building your registration website…' } },
  { phase: 3, produce: 'website', span: { node: 'vercel.deploy', ms: 2400, cost: 0.0030 }, msg: { from: 'sai', text: 'Your website is live 🎉 Preview on the right — berkeley-ai-hack.vercel.app' } },

  { phase: 3, tier: 1, sai: { node: 'exec.browserbase', log: 'headless: Slack workspace + channels' }, span: { node: 'browserbase.slack', ms: 5200, cost: 0.0050 }, produce: 'slack', msg: { from: 'sai', text: 'Setting up your community Slack…' } },
  { phase: 3, produce: 'devpost', sai: { log: 'Devpost DOM changed → graceful fallback' }, span: { node: 'browserbase.devpost', ms: 3800, cost: 0.0040, warn: true }, msg: { from: 'sai', text: "Slack is ready — 5 channels set up. One heads-up: I couldn't auto-create the Devpost page (their site changed), so I left you a 2-minute manual guide. Everything else is done." } },

  { phase: 3, tier: 3, produce: 'outreach', sai: { node: 'exec.outreach', log: 'drafts only — NOT sent (Tier 3)' }, span: { node: 'outreach.draft', ms: 2900, cost: 0.0150 }, msg: { from: 'sai', text: "I drafted 3 sponsor emails for you to review — on the right. I won't send anything without your OK." } },

  // PHASE 4 — High-stakes handoff (decision stays in chat)
  { phase: 4, tier: 3, sai: { node: 'gate.handoff', log: 'paused — Tier 3 handoff' }, msg: { from: 'sai', text: 'Two things need your call:\n• Send the 3 sponsor emails?\n• Grab the domain berkeleyaihack.com for $12?', actions: [
    { label: 'Send the emails', kind: 'danger', reply: 'Send them' },
    { label: 'Buy domain ($12)', kind: 'danger', reply: 'Buy the domain' },
    { label: 'Skip for now', kind: 'line', reply: 'Skip for now' },
  ] } },

  // PHASE 5 — Delivery
  { phase: 5, status: 'done', sai: { stat: 'done', node: 'deliver', log: 'run complete' }, msg: { from: 'sai', text: "You're all set 🎉\n\n• Website: berkeley-ai-hack.vercel.app\n• Slack: 5 channels ready\n• Devpost: quick manual guide\n• Brand assets: saved\n• Sponsor emails: ready when you are\n\nYou answered a few questions. I did the rest." } },
]
