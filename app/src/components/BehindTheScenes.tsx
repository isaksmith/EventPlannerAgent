import { PHASES } from '../orchestrator/demoScript'
import type { OrchestratorState } from '../orchestrator/useOrchestrator'

function Pill({ text, kind }: { text: string; kind: 'idle' | 'coral' | 'olive' | 'ochre' | 'brick' }) {
  const map: Record<string, string> = {
    idle: 'bg-surface2 text-inkSoft border-line',
    coral: 'bg-coral/10 text-coralDeep border-coral/40',
    olive: 'bg-olive/15 text-olive border-olive/40',
    ochre: 'bg-ochre/15 text-ochre border-ochre/40',
    brick: 'bg-brick/12 text-brick border-brick/40',
  }
  return <span className={'text-[10px] mono px-2 py-0.5 rounded-full border ' + (map[kind] || map.idle)}>{text}</span>
}

const TIERS = [
  { n: 1, c: '#7E8C57', t: 'Tier 1 · Auto', d: 'reversible · no money · no relationships → just runs' },
  { n: 2, c: '#BC8A2E', t: 'Tier 2 · Confirm plan', d: 'sets direction → pause once for approval' },
  { n: 3, c: '#B2553B', t: 'Tier 3 · Human handoff', d: 'money / real people / mass-send → draft only, ask first' },
]

export function BehindTheScenes({ open, onClose, s }: { open: boolean; onClose: () => void; s: OrchestratorState }) {
  const totalMs = s.spans.reduce((a, b) => a + b.ms, 0)
  const totalCost = s.spans.reduce((a, b) => a + b.cost, 0)
  return (
    <>
      <div className="fixed inset-0 z-40 transition-opacity duration-200"
        style={{ background: 'rgba(27,26,23,.4)', opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none' }}
        onClick={onClose} />
      <aside className="fixed top-0 right-0 h-full w-[440px] max-w-[92vw] bg-canvas border-l border-line z-50 overflow-y-auto transition-transform duration-300"
        style={{ transform: open ? 'translateX(0)' : 'translateX(100%)' }}>
        <div className="sticky top-0 bg-canvas/95 backdrop-blur px-4 py-3 border-b border-line flex items-center gap-2">
          <div>
            <div className="text-sm font-semibold">Behind the scenes</div>
            <div className="text-[11px] text-inkSoft">what Marquee is running — for transparency</div>
          </div>
          <button onClick={onClose} className="ml-auto h-8 w-8 rounded-md border border-line text-inkSoft hover:bg-surface2">×</button>
        </div>
        <div className="p-4 space-y-4">
          <div className="rounded-xl border border-line bg-surface p-4">
            <h3 className="text-sm font-semibold mb-3">Progress</h3>
            <div className="flex flex-wrap items-center gap-1 text-[11px]">
              {PHASES.map((p, i) => (
                <div key={p} className="flex items-center gap-1">
                  <span className={'px-2 py-1 rounded-md border ' + (i < s.phase ? 'border-line text-inkSoft bg-surface2' : i === s.phase ? 'border-coral/60 text-coralDeep bg-coral/10 glow' : 'border-line text-inkSoft/60')}>{i}· {p}</span>
                  {i < PHASES.length - 1 && <span className="text-line">→</span>}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Marquee <span className="text-inkSoft font-normal">· dispatcher</span></h3>
              <Pill text={s.sai.stat} kind={s.sai.stat === 'active' ? 'olive' : s.sai.stat === 'done' ? 'coral' : 'idle'} />
            </div>
            <div className="space-y-2 text-xs">
              <div><span className="text-inkSoft">intent:</span> <span className="mono text-coralDeep">{s.sai.intent}</span></div>
              <div><span className="text-inkSoft">state node:</span> <span className="mono text-clay">{s.sai.node}</span></div>
              <div className="text-inkSoft pt-1">activity</div>
              <div className="mono text-[11px] space-y-1 text-inkSoft max-h-28 overflow-y-auto">
                {s.sai.log.map((l, i) => <div key={i}>› {l}</div>)}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Redis <span className="text-inkSoft font-normal">· event profile</span></h3>
              <Pill text={s.profile.status} kind={Object.keys(s.profile.event).length ? 'coral' : 'idle'} />
            </div>
            <pre className="mono text-[10.5px] leading-relaxed text-ink max-h-44 overflow-y-auto bg-surface2 rounded-lg p-2.5 border border-line">{JSON.stringify(s.profile, null, 1)}</pre>
          </div>

          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Browserbase <span className="text-inkSoft font-normal">· headless</span></h3>
              <Pill text={s.bbStatus} kind={s.bbStatus === 'done' ? 'olive' : 'idle'} />
            </div>
            <div className="space-y-1.5 text-[11px] mono">
              {s.bbLog.map((l, i) => (
                <div key={i} style={{ color: l.tone === 'ok' ? '#586237' : l.tone === 'warn' ? '#8a6516' : '#6E6A63' }}>{l.text}</div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Arize AI <span className="text-inkSoft font-normal">· trace</span></h3>
              <Pill text={s.spans.length + ' spans'} kind="idle" />
            </div>
            <div className="space-y-1 text-[10px] mono max-h-40 overflow-y-auto">
              {s.spans.map((sp, i) => (
                <div key={i} className="flex justify-between" style={{ color: sp.warn ? '#8a6516' : '#6E6A63' }}>
                  <span>{sp.warn ? '⚠' : '•'} {sp.node}</span>
                  <span style={{ color: '#9A857B' }}>{sp.ms}ms · ${sp.cost.toFixed(4)}</span>
                </div>
              ))}
            </div>
            <div className="mt-2 pt-2 border-t border-line flex justify-between text-[10px] text-inkSoft">
              <span>total</span>
              <span className="mono">{totalMs.toLocaleString()} ms · ${totalCost.toFixed(3)}</span>
            </div>
          </div>

          <div className="rounded-xl border border-line bg-surface p-4">
            <h3 className="text-sm font-semibold mb-3">How Marquee decides <span className="text-inkSoft font-normal">· autonomy</span></h3>
            <div className="space-y-2">
              {TIERS.map((tier) => (
                <div key={tier.n} className={'rounded-lg border border-line p-2.5 ' + (s.activeTier === tier.n ? 'glow' : '')}>
                  <div className="flex items-center gap-2 text-xs font-medium"><span className="h-2 w-2 rounded-full" style={{ background: tier.c }} /> {tier.t}</div>
                  <div className="text-[10px] text-inkSoft mt-1">{tier.d}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
