import { STATUS } from '../orchestrator/demoScript'
import { META, ORDER } from './Tiles'
import type { DeliverableKey, Phase } from '../types'

export function Header(props: {
  phase: Phase
  auto: boolean
  nextLabel: string
  nextDisabled: boolean
  available: DeliverableKey[]
  openPanels: DeliverableKey[]
  onNext: () => void
  onAuto: () => void
  onReset: () => void
  onToggleChip: (k: DeliverableKey) => void
  onOpenDrawer: () => void
}) {
  const { phase, auto, nextLabel, nextDisabled, available, openPanels } = props
  const tone = phase === 5 ? 'border-olive/50 text-olive bg-olive/10'
    : phase === 4 ? 'border-brick/50 text-brick bg-brick/10'
    : 'border-coral/40 text-coralDeep bg-coral/10'
  return (
    <header className="border-b border-line bg-canvas/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-[1500px] mx-auto px-4 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <svg width="32" height="28" viewBox="0 0 32 28" aria-hidden="true">
            <path d="M10 7 L16 2 L22 7" fill="none" stroke="#CC785C" strokeWidth="2" strokeLinecap="round" />
            <rect x="3" y="7" width="26" height="15" rx="4" fill="#CC785C" />
            <circle cx="10" cy="14.5" r="2" fill="#FBF9F4" /><circle cx="16" cy="14.5" r="2" fill="#FBF9F4" /><circle cx="22" cy="14.5" r="2" fill="#FBF9F4" />
          </svg>
          <div>
            <div className="font-display text-[19px] font-semibold tracking-tight leading-none">Marquee</div>
            <div className="text-[11px] text-inkSoft leading-none mt-1">plan your whole event by chat</div>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-inkSoft/70 mr-1 hidden md:block">demo</span>
          <button onClick={props.onReset} className="px-3 py-1.5 rounded-lg text-sm border border-line text-inkSoft hover:bg-surface2">Reset</button>
          <button onClick={props.onAuto} className="px-3 py-1.5 rounded-lg text-sm border border-line text-inkSoft hover:bg-surface2">{auto ? '⏸ Pause' : '▶ Auto-play'}</button>
          <button onClick={props.onNext} disabled={nextDisabled} className="px-4 py-1.5 rounded-lg text-sm font-medium text-surface disabled:opacity-40" style={{ background: '#B05E40' }}>{nextLabel}</button>
        </div>
      </div>
      <div className="max-w-[1500px] mx-auto px-4 pb-3 flex items-center gap-3">
        <span className={'text-[11px] px-2.5 py-1 rounded-full border shrink-0 ' + tone}>{STATUS[phase]}</span>
        <div className="h-4 w-px bg-line hidden sm:block" />
        <div className="flex items-center gap-2 flex-wrap">
          {ORDER.filter((k) => available.includes(k)).map((k) => (
            <button key={k} className={'chip' + (openPanels.includes(k) ? ' chip-on' : '')} onClick={() => props.onToggleChip(k)}>
              <span>{META[k].icon}</span> {META[k].label}
            </button>
          ))}
          {available.length === 0 && (
            <span className="text-[11px] text-inkSoft/80">Your branding, website &amp; outreach appear here as they're ready.</span>
          )}
        </div>
        <button onClick={props.onOpenDrawer} className="ml-auto shrink-0 text-[12px] px-3 py-1.5 rounded-lg border border-line text-inkSoft hover:bg-surface2 flex items-center gap-1.5">⚙ Behind the scenes</button>
      </div>
    </header>
  )
}
