// ============================================================================
// useOrchestrator — drives the demo timeline and (mocked) integration calls.
// ----------------------------------------------------------------------------
// This hook is the seam between "scripted demo" and "real engine". Today it
// plays demoScript.ts step-by-step. To go live, replace `advance()`'s scripted
// progression with a real Sai-driven loop — but KEEP calling the same
// `integrations` services (memory/brand/deploy/browserbase/outreach/tracer),
// since the UI already renders entirely from the state this hook produces.
// ============================================================================
import { useReducer, useRef } from 'react'
import { getIntegrations } from '../integrations'
import { demoScript, type Step, type Produce } from './demoScript'
import type {
  Phase, ProfileStatus, EventProfile, ChatMessage, ChatAction, DeliverableKey,
  ArizeSpan, BrandKit, SiteResult, EmailDraft,
} from '../types'

interface Dispatcher { stat: 'idle' | 'active' | 'done'; intent: string; node: string; log: string[] }
interface BbLine { text: string; tone: 'ok' | 'warn' | 'muted' }
interface Deliverables { branding?: BrandKit; website?: SiteResult; outreach?: EmailDraft[] }

export interface OrchestratorState {
  idx: number
  phase: Phase
  status: ProfileStatus
  done: boolean
  waiting: boolean
  auto: boolean
  messages: ChatMessage[]
  pendingActions: ChatAction[] | null
  profile: EventProfile
  deliverables: Deliverables
  openPanels: DeliverableKey[]
  spans: ArizeSpan[]
  sai: Dispatcher
  bbLog: BbLine[]
  bbStatus: string
  activeTier: 1 | 2 | 3 | null
}

export interface Orchestrator {
  state: OrchestratorState
  next: () => void
  answer: (a: ChatAction) => void
  toggleAuto: () => void
  reset: () => void
  togglePanel: (k: DeliverableKey) => void
}

function emptyProfile(): EventProfile {
  return {
    session_id: 'session:demo-001', status: 'interviewing',
    event: {}, audience: {}, aesthetic: {}, ops: {}, outreach: {}, artifacts: {},
  }
}
function initialState(): OrchestratorState {
  return {
    idx: -1, phase: 0, status: 'interviewing', done: false, waiting: false, auto: false,
    messages: [], pendingActions: null, profile: emptyProfile(),
    deliverables: {}, openPanels: [], spans: [],
    sai: { stat: 'idle', intent: '—', node: 'init', log: [] },
    bbLog: [], bbStatus: 'waiting', activeTier: null,
  }
}

export function useOrchestrator(): Orchestrator {
  const integrationsRef = useRef(getIntegrations())
  const ref = useRef<OrchestratorState>(initialState())
  const [, force] = useReducer((x) => x + 1, 0)
  const busy = useRef(false)
  const timer = useRef<number | undefined>(undefined)

  function openPanel(key: DeliverableKey) {
    const st = ref.current
    if (!st.openPanels.includes(key)) st.openPanels = [...st.openPanels, key]
  }

  async function produce(kind: Produce) {
    const st = ref.current
    const ix = integrationsRef.current
    if (kind === 'branding') {
      st.deliverables.branding = await ix.brand.generateBrandKit(st.profile)
      openPanel('branding')
    } else if (kind === 'website') {
      const site = await ix.deploy.buildAndDeploy(st.profile, st.deliverables.branding!)
      st.deliverables.website = site
      await ix.memory.set('artifacts.site_url', 'https://' + site.url)
      st.profile = await ix.memory.getProfile()
      openPanel('website')
    } else if (kind === 'slack') {
      const r = await ix.browserbase.provisionSlack(st.profile)
      st.bbStatus = 'done'
      st.bbLog = [
        ...st.bbLog,
        { text: '✓ Slack workspace created', tone: 'ok' },
        ...(r.channels ?? []).map((c) => ({ text: '+ ' + c, tone: 'muted' as const })),
      ]
    } else if (kind === 'devpost') {
      const r = await ix.browserbase.createDevpost(st.profile)
      if (!r.ok) {
        st.bbLog = [
          ...st.bbLog,
          { text: '⚠ Devpost: ' + r.fallback, tone: 'warn' },
          { text: '→ run continues (no crash)', tone: 'muted' },
        ]
      }
    } else if (kind === 'outreach') {
      st.deliverables.outreach = await ix.outreach.draftSponsorEmails(st.profile)
      openPanel('outreach')
    }
  }

  async function applyStep(step: Step) {
    const st = ref.current
    const ix = integrationsRef.current
    if (step.phase !== undefined) st.phase = step.phase
    if (step.tier) st.activeTier = step.tier
    if (step.sai) {
      if (step.sai.stat) st.sai.stat = step.sai.stat
      if (step.sai.intent) st.sai.intent = step.sai.intent
      if (step.sai.node) st.sai.node = step.sai.node
      if (step.sai.log) st.sai.log = [...st.sai.log, step.sai.log]
    }
    if (step.status) {
      st.status = step.status
      await ix.memory.set('status', step.status)
      st.profile = await ix.memory.getProfile()
    }
    if (step.write) {
      for (const [p, v] of step.write) await ix.memory.set(p, v)
      st.profile = await ix.memory.getProfile()
    }
    if (step.span) {
      const s = step.span
      st.spans = [...st.spans, ix.tracer.span(s.node, s.ms, s.cost, s.warn)]
    }
    if (step.produce) await produce(step.produce)
    if (step.msg) {
      st.messages = [...st.messages, { from: step.msg.from, text: step.msg.text }]
      st.pendingActions = step.msg.actions ?? null
      st.waiting = !!step.msg.actions
    }
    force()
  }

  async function advance() {
    const st = ref.current
    if (busy.current || st.waiting || st.done) return
    if (st.idx >= demoScript.length - 1) { st.done = true; stopAuto(); force(); return }
    busy.current = true
    st.idx += 1
    await applyStep(demoScript[st.idx])
    busy.current = false
  }

  function next() { void advance() }

  function answer(action: ChatAction) {
    const st = ref.current
    st.messages = [...st.messages, { from: 'user', text: action.reply }]
    st.pendingActions = null
    st.waiting = false
    force()
    void advance()
  }

  function tick() {
    if (!ref.current.auto) return
    if (!ref.current.waiting && !ref.current.done) void advance()
    timer.current = window.setTimeout(tick, ref.current.waiting ? 700 : 1300)
  }
  function startAuto() { ref.current.auto = true; force(); tick() }
  function stopAuto() { ref.current.auto = false; if (timer.current) clearTimeout(timer.current); force() }
  function toggleAuto() { ref.current.auto ? stopAuto() : startAuto() }

  function togglePanel(key: DeliverableKey) {
    const st = ref.current
    st.openPanels = st.openPanels.includes(key)
      ? st.openPanels.filter((k) => k !== key)
      : [...st.openPanels, key]
    force()
  }

  function reset() {
    stopAuto()
    integrationsRef.current = getIntegrations()
    ref.current = initialState()
    busy.current = false
    force()
  }

  return { state: ref.current, next, answer, toggleAuto, reset, togglePanel }
}
