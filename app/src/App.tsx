import { useEffect, useState } from 'react'
import { apiBase as getApiBase, setApiBase, deleteSession } from './api/client'
import { useOrchestrator } from './orchestrator/useOrchestrator'
import { useLiveOrchestrator } from './orchestrator/useLiveOrchestrator'
import { ORDER, TileGrid, MaximizeModal } from './components/Tiles'
import { Header } from './components/Header'
import { ChatPanel } from './components/ChatPanel'
import { BehindTheScenes } from './components/BehindTheScenes'
import type { DeliverableKey } from './types'

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

  const available = ORDER.filter((k) => Boolean(s.deliverables[k]))
  const n = s.openPanels.length || ORDER.length
  const basis = chatExpanded ? '100%' : n <= 2 ? '50%' : n === 3 ? '44%' : '38%'
  const nextLabel = s.done ? 'Done' : s.waiting ? 'Reply in chat' : 'Next'

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
