import { STATUS } from '../orchestrator/demoScript'
import { META, ORDER } from './Tiles'
import { PastEvents } from './PastEvents'
import { Icon } from './Icon'
import type { DeliverableKey, Phase } from '../types'

export function Header(props: {
  phase: Phase
  auto: boolean
  live: boolean
  apiBase: string
  nextLabel: string
  nextDisabled: boolean
  available: DeliverableKey[]
  openPanels: DeliverableKey[]
  onNext: () => void
  onAuto: () => void
  onReset: () => void
  onPlanNewEvent: () => void
  onToggleLive: () => void
  onApiBaseChange: (v: string) => void
  onToggleChip: (k: DeliverableKey) => void
  onOpenDrawer: () => void
}) {
  const { phase, auto, live, nextLabel, nextDisabled, available, openPanels } = props
  const tone = phase === 5 ? 'border-olive/50 text-olive bg-olive/10'
    : phase === 4 ? 'border-brick/50 text-brick bg-brick/10'
    : 'border-coral/40 text-coralDeep bg-coral/10'
  return (
    <header className="border-b border-line bg-canvas/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-[1500px] mx-auto px-4 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <a href="https://landing-ten-ochre-58.vercel.app" target="_blank" rel="noreferrer" className="h-9 w-9 rounded-xl grid place-items-center text-surface font-semibold shrink-0 shadow-sm transition-transform hover:scale-105 hover:brightness-110" style={{ background: '#CC785C' }} aria-label="Back to Marquee landing page" title="Back to landing page">M</a>
          <div>
            <div className="font-display text-[19px] font-semibold tracking-tight leading-none">Marquee</div>
            <div className="text-[11px] text-inkSoft leading-none mt-1">{live ? 'live backend' : 'plan your whole event by chat'}</div>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2 flex-wrap justify-end">
          {live && (
            <input
              value={props.apiBase}
              onChange={(e) => props.onApiBaseChange(e.target.value)}
              className="hidden lg:block w-40 px-2 py-1 rounded-lg text-[11px] mono bg-surface2 border border-line text-inkSoft"
              title="Backend API URL"
            />
          )}
          <div
            className="inline-flex rounded-lg border border-line p-0.5 bg-surface2 text-[12px] font-medium"
            role="group"
            aria-label="Demo or live backend"
          >
            <button
              type="button"
              onClick={() => { if (live) props.onToggleLive() }}
              className={'px-3 py-1 rounded-md transition-colors ' + (live ? 'text-inkSoft hover:text-ink' : 'bg-surface text-ink shadow-sm')}
              aria-pressed={!live}
            >
              Demo
            </button>
            <button
              type="button"
              onClick={() => { if (!live) props.onToggleLive() }}
              className={'px-3 py-1 rounded-md transition-colors ' + (live ? 'bg-olive/15 text-olive border border-olive/30 shadow-sm' : 'text-inkSoft hover:text-ink')}
              aria-pressed={live}
            >
              Live
            </button>
          </div>
          <PastEvents />
          <button onClick={props.onReset} className="px-3 py-1.5 rounded-lg text-sm border border-line text-inkSoft hover:bg-surface2 hover:text-ink" title="Reset current mode only">
            Reset
          </button>
          <button
            onClick={props.onPlanNewEvent}
            className="px-3 py-1.5 rounded-lg text-sm font-medium text-surface inline-flex items-center gap-1.5 hover:brightness-110"
            style={{ background: '#B05E40' }}
            title="Start fresh — clears live session and demo progress"
          >
            <Icon name="sparkles" size={15} /> Plan new event
          </button>
          {!live && (
            <>
              <button onClick={props.onAuto} className="px-3 py-1.5 rounded-lg text-sm border border-line text-inkSoft hover:bg-surface2 hover:text-ink inline-flex items-center gap-1.5"><Icon name={auto ? 'pause' : 'play'} size={14} />{auto ? 'Pause' : 'Auto-play'}</button>
              <button onClick={props.onNext} disabled={nextDisabled} className="px-4 py-1.5 rounded-lg text-sm font-medium text-surface disabled:opacity-40 hover:brightness-110" style={{ background: '#B05E40' }}>{nextLabel}</button>
            </>
          )}
        </div>
      </div>
      <div className="max-w-[1500px] mx-auto px-4 pb-3 flex items-center gap-3">
        <span className={'text-[11px] px-2.5 py-1 rounded-full border shrink-0 ' + tone}>{STATUS[phase]}</span>
        <div className="h-4 w-px bg-line hidden sm:block" />
        <div className="flex items-center gap-2 flex-wrap">
          {ORDER.filter((k) => available.includes(k)).map((k) => (
            <button key={k} className={'chip' + (openPanels.includes(k) ? ' chip-on' : '')} aria-pressed={openPanels.includes(k)} onClick={() => props.onToggleChip(k)}>
              <Icon name={META[k].icon} size={14} /> {META[k].label}
            </button>
          ))}
          {available.length === 0 && (
            <span className="text-[11px] text-inkSoft/80">Your branding, website &amp; outreach appear here as they're ready.</span>
          )}
        </div>
        <button onClick={props.onOpenDrawer} className="ml-auto shrink-0 text-[12px] px-3 py-1.5 rounded-lg border border-line text-inkSoft hover:bg-surface2 hover:text-ink flex items-center gap-1.5"><Icon name="sliders" size={14} /> Behind the scenes</button>
      </div>
    </header>
  )
}
