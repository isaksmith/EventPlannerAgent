import { useEffect, useState } from 'react'
import { apiBase as getApiBase, setApiBase, deleteSession, fetchEvent, assetUrl, backendUrl, type PastEvent } from './api/client'
import { useOrchestrator } from './orchestrator/useOrchestrator'
import { useLiveOrchestrator } from './orchestrator/useLiveOrchestrator'
import { ORDER, TileGrid, MaximizeModal, type Deliverables } from './components/Tiles'
import { Header } from './components/Header'
import { ChatPanel } from './components/ChatPanel'
import { BehindTheScenes } from './components/BehindTheScenes'
import { Icon } from './components/Icon'
import type { DeliverableKey, BrandKit, SiteResult, EmailDraft, LocationInfo } from './types'

const LIVE_KEY = 'marquee_live'
const API_KEY = 'marquee_api_base'

export default function App() {
  const [live, setLive] = useState(() => localStorage.getItem(LIVE_KEY) === '1')
  const [apiUrl, setApiUrl] = useState(() => {
    if (import.meta.env.DEV) return 'http://127.0.0.1:8000'
    return localStorage.getItem(API_KEY) || getApiBase()
  })
  const [modal, setModal] = useState<DeliverableKey | null>(null)
  const [drawer, setDrawer] = useState(false)
  const [chatExpanded, setChatExpanded] = useState(false)
  const [pastEvent, setPastEvent] = useState<{ ev: PastEvent; deliverables: Deliverables; messages: { from: 'sai' | 'user'; text: string }[] } | null>(null)

  const demo = useOrchestrator()
  const liveOrch = useLiveOrchestrator(live)
  const orch = live ? liveOrch : demo
  const s = orch.state

  useEffect(() => { setApiBase(apiUrl) }, [apiUrl])

  useEffect(() => {
    if (live) return
    if (demo.state.idx >= 0) return
    // Auto-play the first few steps on mount so the welcome exchange is visible.
    void (async () => {
      demo.next()
      await new Promise((r) => setTimeout(r, 400))
      demo.next()
      await new Promise((r) => setTimeout(r, 400))
      demo.next()
      await new Promise((r) => setTimeout(r, 400))
      demo.next()
    })()
  }, [live, demo])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.code === 'Escape') { setModal(null); setDrawer(false) }
      if (live) return
      const tag = document.activeElement?.tagName ?? ''
      if (e.code === 'Space' && !/INPUT|TEXTAREA/.test(tag)) { e.preventDefault(); demo.next() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [live, demo])

  async function planNewEvent() {
    liveOrch.reset()
    demo.reset()
    setModal(null)
    setDrawer(false)
    setChatExpanded(false)
    try { await deleteSession() } catch { /* ok if no session or backend unreachable */ }
  }

  function toggleLive() {
    const next = !live
    setLive(next)
    localStorage.setItem(LIVE_KEY, next ? '1' : '0')
    if (next) liveOrch.reset()
    else demo.reset()
  }

  async function viewPastEvent(ev: PastEvent) {
    try {
      const full = await fetchEvent(ev.id)
      const profile = full.profile as Record<string, unknown> | null
      const artifacts = (profile?.['artifacts'] as Record<string, unknown> | undefined) || {}
      const event = (profile?.['event'] as Record<string, unknown> | undefined) || {}
      const aesthetic = (profile?.['aesthetic'] as Record<string, unknown> | undefined) || {}

      // Build brand kit from archived assets
      const brandFiles = full.brand_files || []
      const logoFile = brandFiles.find((f) => f.name.startsWith('logo.'))
      const heroFile = brandFiles.find((f) => f.name.startsWith('invite_hero.') || f.name.startsWith('hero.'))
      const assets = brandFiles.map((f) => ({ label: f.name.replace(/\.[^.]+$/, ''), imageUrl: assetUrl(f.url) }))
      const colors = (full.colors || []) as string[]
      const palette = colors.length > 0
        ? colors.map((c, i) => ({ hex: c, name: `Color ${i + 1}` }))
        : [{ hex: '#CC785C', name: 'Coral' }, { hex: '#1B1A17', name: 'Ink' }]
      const branding: BrandKit = {
        vibe: full.vibe || '',
        logo: { text: (event['name'] as string || 'EV').slice(0, 4), accent: colors[0] || '#CC785C', bg: '#1B1A17', imageUrl: logoFile ? assetUrl(logoFile.url) : undefined },
        heroImageUrl: heroFile ? assetUrl(heroFile.url) : undefined,
        palette,
        assets,
        generatedBy: 'openrouter',
      }

      // Build site result
      const website: SiteResult | undefined = full.site_url
        ? { url: backendUrl(full.site_url).replace(/^https?:\/\//, ''), eyebrow: (event['type'] as string || 'event').toUpperCase(), title: full.name, subtitle: [full.attendees ? `${full.attendees} attendees` : '', full.location || ''].filter(Boolean).join(' · ') }
        : undefined

      // Build location
      const location: LocationInfo | undefined = full.location ? { label: full.location, query: full.location } : undefined

      // Build outreach drafts
      const drafts = (artifacts['outreach_drafts'] as string[]) || []
      const outreach: EmailDraft[] | undefined = drafts.length > 0
        ? drafts.map((d, i) => ({ to: `sponsor${i + 1}`, subject: `Sponsor outreach draft ${i + 1}`, body: d }))
        : undefined

      const deliverables: Deliverables = { branding, website, location, outreach }
      const messages = [
        { from: 'sai' as const, text: `Welcome to Marquee! This is the archived view for "${full.name}".` },
        { from: 'sai' as const, text: `Event: ${full.name} · ${full.dates || ''} · ${full.location || ''}` },
      ]
      setPastEvent({ ev: full, deliverables, messages })
      setModal(null)
      setDrawer(false)
      setChatExpanded(false)
    } catch (e) {
      console.error('Failed to load past event', e)
    }
  }

  function exitPastEvent() {
    setPastEvent(null)
  }

  const available = ORDER.filter((k) => Boolean(pastEvent ? pastEvent.deliverables[k] : s.deliverables[k]))
  const n = pastEvent ? (pastEvent.deliverables && ORDER.filter((k) => pastEvent.deliverables[k]).length) || ORDER.length : (s.openPanels.length || ORDER.length)
  const basis = chatExpanded ? '100%' : n <= 2 ? '50%' : n === 3 ? '44%' : '38%'
  const nextLabel = s.done ? 'Done' : s.waiting ? 'Reply in chat' : 'Next'

  if (pastEvent) {
    return (
      <>
        <Header
          phase={5}
          auto={false}
          live={false}
          apiBase={apiUrl}
          nextLabel="Back to current"
          nextDisabled={false}
          available={available}
          openPanels={ORDER}
          onNext={exitPastEvent}
          onAuto={() => {}}
          onReset={exitPastEvent}
          onPlanNewEvent={exitPastEvent}
          onToggleLive={() => {}}
          onApiBaseChange={() => {}}
          onToggleChip={() => {}}
          onOpenDrawer={() => setDrawer(true)}
        />
        <div className="border-b border-line bg-coral/5 px-4 py-2 text-[12px] text-inkSoft flex items-center gap-2">
          <Icon name="folder" size={14} />
          Viewing archived event: <strong className="text-ink">{pastEvent.ev.name}</strong>
          <span className="text-inkSoft/60">· {pastEvent.ev.dates || ''} · {pastEvent.ev.location || ''}</span>
          <button onClick={exitPastEvent} className="ml-auto text-clay hover:text-coralDeep font-medium">← Back to current</button>
        </div>
        <main className="max-w-[1500px] mx-auto px-4 py-3">
          <div className="flex gap-4" style={{ height: 'calc(100vh - 160px)', minHeight: 420 }}>
            <div className="h-full" style={{ flex: `0 0 ${basis}`, transition: 'flex-basis .35s cubic-bezier(.2,.7,.2,1)' }}>
              <ChatPanel
                messages={pastEvent.messages}
                pendingActions={[]}
                onAnswer={() => {}}
                live={false}
                expanded={chatExpanded}
                onToggleExpand={() => setChatExpanded((v) => !v)}
              />
            </div>
            {!chatExpanded && (
              <TileGrid
                open={ORDER}
                deliverables={pastEvent.deliverables}
                cols={n <= 1 ? 1 : 2}
                onMaximize={setModal}
                onClose={() => {}}
                placeholder={false}
              />
            )}
          </div>
        </main>
        <MaximizeModal k={modal} deliverables={pastEvent.deliverables} onClose={() => setModal(null)} />
        <BehindTheScenes open={drawer} onClose={() => setDrawer(false)} s={s} />
      </>
    )
  }

  return (
    <>
      <Header
        phase={s.phase}
        auto={s.auto}
        live={live}
        apiBase={apiUrl}
        nextLabel={nextLabel}
        nextDisabled={s.waiting || s.done}
        available={available}
        openPanels={s.openPanels}
        onNext={orch.next}
        onAuto={orch.toggleAuto}
        onReset={orch.reset}
        onPlanNewEvent={planNewEvent}
        onToggleLive={toggleLive}
        onApiBaseChange={(v) => { setApiUrl(v); localStorage.setItem(API_KEY, v) }}
        onToggleChip={orch.togglePanel}
        onOpenDrawer={() => setDrawer(true)}
        onViewEvent={viewPastEvent}
      />

      <main className="max-w-[1500px] mx-auto px-4 py-3">
        <div className="flex gap-4" style={{ height: 'calc(100vh - 116px)', minHeight: 420 }}>
          <div className="h-full" style={{ flex: `0 0 ${chatExpanded ? '100%' : basis}`, transition: 'flex-basis .35s cubic-bezier(.2,.7,.2,1)' }}>
            <ChatPanel
              messages={s.messages}
              pendingActions={s.pendingActions}
              onAnswer={orch.answer}
              live={live}
              onSend={live ? liveOrch.send : undefined}
              sending={live ? liveOrch.sending : false}
              expanded={chatExpanded}
              onToggleExpand={() => setChatExpanded((v) => !v)}
            />
          </div>
          {!chatExpanded && (
            <TileGrid
              open={s.openPanels.length > 0 ? s.openPanels : ORDER}
              deliverables={s.deliverables}
              cols={n <= 1 ? 1 : 2}
              onMaximize={setModal}
              onClose={orch.togglePanel}
              placeholder={s.openPanels.length === 0}
            />
          )}
        </div>
      </main>

      <MaximizeModal k={modal} deliverables={s.deliverables} onClose={() => setModal(null)} />
      <BehindTheScenes open={drawer} onClose={() => setDrawer(false)} s={s} />
    </>
  )
}
