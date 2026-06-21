import { useEffect, useState } from 'react'
import { useOrchestrator } from './orchestrator/useOrchestrator'
import { ORDER, TileGrid, MaximizeModal } from './components/Tiles'
import { Header } from './components/Header'
import { ChatPanel } from './components/ChatPanel'
import { BehindTheScenes } from './components/BehindTheScenes'
import type { DeliverableKey } from './types'

export default function App() {
  const orch = useOrchestrator()
  const s = orch.state
  const [modal, setModal] = useState<DeliverableKey | null>(null)
  const [drawer, setDrawer] = useState(false)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.code === 'Escape') { setModal(null); setDrawer(false) }
      const tag = document.activeElement?.tagName ?? ''
      if (e.code === 'Space' && !/INPUT|TEXTAREA/.test(tag)) { e.preventDefault(); orch.next() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [orch])

  const available = ORDER.filter((k) => Boolean(s.deliverables[k]))
  const n = s.openPanels.length
  const basis = n === 0 ? '100%' : n <= 2 ? '50%' : n === 3 ? '44%' : '38%'
  const nextLabel = s.done ? '✓ Done' : s.waiting ? '✋ reply in chat' : 'Next ▸'

  return (
    <>
      <Header
        phase={s.phase}
        auto={s.auto}
        nextLabel={nextLabel}
        nextDisabled={s.waiting || s.done}
        available={available}
        openPanels={s.openPanels}
        onNext={orch.next}
        onAuto={orch.toggleAuto}
        onReset={orch.reset}
        onToggleChip={orch.togglePanel}
        onOpenDrawer={() => setDrawer(true)}
      />

      <main className="max-w-[1500px] mx-auto px-4 py-3">
        <div className="flex gap-4" style={{ height: 'calc(100vh - 116px)', minHeight: 420 }}>
          <div className="h-full" style={{ flex: `0 0 ${basis}`, transition: 'flex-basis .35s cubic-bezier(.2,.7,.2,1)' }}>
            <ChatPanel messages={s.messages} pendingActions={s.pendingActions} onAnswer={orch.answer} />
          </div>
          {n > 0 && (
            <TileGrid
              open={s.openPanels}
              deliverables={s.deliverables}
              cols={n <= 1 ? 1 : 2}
              onMaximize={setModal}
              onClose={orch.togglePanel}
            />
          )}
        </div>
      </main>

      <MaximizeModal k={modal} deliverables={s.deliverables} onClose={() => setModal(null)} />
      <BehindTheScenes open={drawer} onClose={() => setDrawer(false)} s={s} />
    </>
  )
}
