import type {
  ArizeSpan,
  BrandKit,
  DeliverableKey,
  EmailDraft,
  EventProfile,
  Phase,
  ProfileStatus,
} from '../types'
import type { Deliverables, OrchestratorState } from './useOrchestrator'
import { assetUrl } from '../api/client'

function statusPhase(status: ProfileStatus): Phase {
  const map: Record<ProfileStatus, Phase> = {
    interviewing: 1,
    awaiting_approval: 2,
    executing: 3,
    awaiting_handoff: 4,
    done: 5,
  }
  return map[status] ?? 0
}

function tierForStatus(status: ProfileStatus): 1 | 2 | 3 | null {
  if (status === 'awaiting_approval') return 2
  if (status === 'executing') return 1
  if (status === 'awaiting_handoff') return 3
  return null
}

function draftFromText(text: string): EmailDraft {
  const toMatch = text.match(/To:\s*(.+)/i)
  const subjMatch = text.match(/Subject:\s*(.+)/i)
  return {
    to: toMatch?.[1]?.trim() || 'sponsor',
    subject: subjMatch?.[1]?.trim() || text.slice(0, 72),
    body: text,
  }
}

function absUrl(_apiBase: string, path: string): string {
  return assetUrl(path)
}

const ASSET_EXT_ORDER = ['webp', 'png', 'jpg', 'jpeg', 'svg'] as const

function urlForStem(
  brandFiles: { name: string; url: string }[],
  stem: string,
): string | undefined {
  for (const ext of ASSET_EXT_ORDER) {
    const hit = brandFiles.find((f) => f.name === `${stem}.${ext}`)
    if (hit) return absUrl('', hit.url)
  }
  return undefined
}

export function profileFromApi(raw: Record<string, unknown>): EventProfile {
  const event = (raw.event as EventProfile['event']) || {}
  const artifacts = (raw.artifacts as EventProfile['artifacts']) || {}
  return {
    session_id: String(raw.session_id || ''),
    status: (raw.status as ProfileStatus) || 'interviewing',
    event,
    audience: (raw.audience as EventProfile['audience']) || {},
    aesthetic: (raw.aesthetic as EventProfile['aesthetic']) || {},
    ops: (raw.ops as EventProfile['ops']) || {},
    outreach: (raw.outreach as EventProfile['outreach']) || {},
    artifacts,
  }
}

function canShowDeliverablePanels(status: ProfileStatus): boolean {
  return status === 'executing' || status === 'awaiting_handoff' || status === 'done'
}

function placeholderBranding(profile: EventProfile): BrandKit {
  const colors = (profile.aesthetic as { colors?: string[] })?.colors || []
  const theme = (profile.aesthetic as { theme?: string })?.theme
  const vibe = theme || profile.aesthetic?.vibe || profile.event?.name || 'Your event'
  return {
    vibe,
    logo: {
      text: (profile.event?.name || 'EV').slice(0, 4).toUpperCase(),
      accent: colors[0] || '#CC785C',
      bg: '#1B1A17',
    },
    palette: [
      { hex: colors[0] || '#CC785C', name: 'Primary' },
      { hex: colors[1] || '#B05E40', name: 'Accent' },
      { hex: '#7E8C57', name: 'Olive' },
      { hex: '#1B1A17', name: 'Ink' },
    ],
    assets: [{ label: 'Generating brand assets…', glyph: '◢' }],
    generatedBy: 'loading',
  }
}

function brandingFromProfile(profile: EventProfile, apiBase: string): BrandKit | undefined {
  const artifacts = profile.artifacts
  const brandFiles = artifacts.brand_files || []
  if (!brandFiles.length) return undefined

  const fileUrl = (name: string) => {
    const hit = brandFiles.find((f) => f.name === name)
    return hit ? absUrl(apiBase, hit.url) : undefined
  }

  const colors = (profile.aesthetic as { colors?: string[] })?.colors || []
  const theme = (profile.aesthetic as { theme?: string })?.theme
  const vibe = theme || profile.aesthetic?.vibe || profile.event?.name || ''
  const logoImageUrl =
    urlForStem(brandFiles, 'invite_motif') || urlForStem(brandFiles, 'logo')
  const heroImageUrl =
    urlForStem(brandFiles, 'invite_cover') ||
    urlForStem(brandFiles, 'invite_hero') ||
    urlForStem(brandFiles, 'hero')
  const promoFile = brandFiles.find((f) => f.name === 'promo.mp4')
  const promoVideoUrl = promoFile ? absUrl(apiBase, promoFile.url) : undefined

  const isGenerated = brandFiles.some(
    (f) => /^invite_.*\.(png|jpe?g|webp)$/i.test(f.name),
  )

  const assets = brandFiles
    .filter((f) => ![
      'logo.png', 'logo.jpg', 'logo.webp', 'logo.svg',
      'hero.png', 'hero.jpg', 'hero.webp', 'hero.svg',
      'invite_cover.webp', 'invite_cover.png', 'invite_cover.jpg', 'invite_cover.svg',
      'invite_hero.webp', 'invite_hero.png', 'invite_hero.jpg', 'invite_hero.svg',
      'invite_motif.webp', 'invite_motif.png', 'invite_motif.jpg', 'invite_motif.svg',
    ].includes(f.name))
    .map((f) => ({
      label: f.label,
      imageUrl: f.name.endsWith('.mp4') ? undefined : absUrl(apiBase, f.url),
      videoUrl: f.name.endsWith('.mp4') ? absUrl(apiBase, f.url) : undefined,
      glyph: f.name.endsWith('.mp4') ? '▶' : '◆',
    }))

  return {
    vibe,
    logo: {
      text: (profile.event?.name || 'EV').slice(0, 4).toUpperCase(),
      accent: colors[0] || '#CC785C',
      bg: '#1B1A17',
      imageUrl: logoImageUrl,
    },
    heroImageUrl: heroImageUrl,
    promoVideoUrl,
    palette: [
      { hex: colors[0] || '#CC785C', name: 'Primary' },
      { hex: colors[1] || '#B05E40', name: 'Accent' },
      { hex: '#7E8C57', name: 'Olive' },
      { hex: '#1B1A17', name: 'Ink' },
    ],
    assets,
    generatedBy: isGenerated ? 'openrouter' : 'stub',
  }
}

export function deliverablesFromProfile(profile: EventProfile, apiBase: string): Deliverables {
  const out: Deliverables = {}
  if (!canShowDeliverablePanels(profile.status)) {
    return out
  }

  const branding = brandingFromProfile(profile, apiBase)
  if (branding) {
    out.branding = branding
  } else if (profile.status === 'executing') {
    out.branding = placeholderBranding(profile)
  }

  if (profile.artifacts?.site_url) {
    const url = profile.artifacts.site_url.replace(/^https?:\/\//, '')
    out.website = {
      url,
      eyebrow: (profile.event?.type || 'event').toUpperCase(),
      title: profile.event?.name || 'Your Event',
      subtitle: `${profile.event?.expected_attendees || '—'} attendees · ${profile.event?.location || 'TBD'}`,
    }
  }
  const drafts = profile.artifacts.outreach_drafts
  if (drafts?.length) {
    out.outreach = drafts.map(draftFromText)
  }
  return out
}

export function panelsForDeliverables(d: Deliverables, prev: DeliverableKey[]): DeliverableKey[] {
  const keys: DeliverableKey[] = []
  if (d.branding) keys.push('branding')
  if (d.website) keys.push('website')
  if (d.outreach) keys.push('outreach')
  return [...new Set([...prev, ...keys])]
}

export function bbFromProfile(profile: EventProfile): { status: string; log: OrchestratorState['bbLog'] } {
  const log: OrchestratorState['bbLog'] = []
  const artifacts = profile.artifacts
  if (artifacts.slack_url) {
    log.push({ text: `✓ Slack: ${artifacts.slack_url}`, tone: 'ok' })
  } else if (profile.ops?.needs_slack) {
    log.push({ text: 'Slack: manual setup guide (see backend)', tone: 'warn' })
  }
  if (artifacts.devpost_url) {
    log.push({ text: `✓ Devpost: ${artifacts.devpost_url}`, tone: 'ok' })
  }
  for (const g of artifacts.fallback_guides || []) {
    log.push({ text: g.split('\n')[0], tone: 'muted' })
  }
  return { status: log.length ? 'done' : 'waiting', log }
}

export function saiFromProfile(profile: EventProfile): OrchestratorState['sai'] {
  const stat = profile.status === 'done' ? 'done' : profile.status === 'executing' ? 'active' : 'idle'
  return { stat, intent: profile.status, node: profile.status, log: [`status=${profile.status}`] }
}

export function spansFromTraces(traces: { name: string; latency_ms: number }[]): ArizeSpan[] {
  return traces.map((t) => ({ node: t.name, ms: t.latency_ms || 0, cost: 0 }))
}

export function gateActions(status: ProfileStatus) {
  if (status === 'awaiting_approval') {
    return [{ label: 'APPROVE', reply: 'APPROVE', kind: 'primary' as const }]
  }
  if (status === 'awaiting_handoff') {
    return [
      { label: 'ALL-SKIP', reply: 'ALL-SKIP', kind: 'line' as const },
      { label: 'FINISH', reply: 'ALL-SKIP', kind: 'primary' as const },
    ]
  }
  return null
}

export function applyProfileToState(st: OrchestratorState, profile: EventProfile, apiBase: string): void {
  st.profile = profile
  st.status = profile.status
  st.phase = statusPhase(profile.status)
  st.activeTier = tierForStatus(profile.status)
  st.sai = saiFromProfile(profile)
  st.deliverables = deliverablesFromProfile(profile, apiBase)
  if (canShowDeliverablePanels(profile.status)) {
    st.openPanels = panelsForDeliverables(st.deliverables, st.openPanels)
    if (profile.status === 'executing' && !st.openPanels.includes('branding')) {
      st.openPanels = ['branding', ...st.openPanels]
    }
  } else {
    st.openPanels = []
  }
  const bb = bbFromProfile(profile)
  st.bbLog = bb.log
  st.bbStatus = bb.status
  st.pendingActions = gateActions(profile.status)
  st.waiting = !!st.pendingActions
  st.done = profile.status === 'done'
}
