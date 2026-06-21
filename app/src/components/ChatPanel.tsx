import { useEffect, useRef } from 'react'
import type { ChatMessage, ChatAction } from '../types'

export function ChatPanel({ messages, pendingActions, onAnswer }: {
  messages: ChatMessage[]
  pendingActions: ChatAction[] | null
  onAnswer: (a: ChatAction) => void
}) {
  const threadRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = threadRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length, pendingActions])

  return (
    <div className="rounded-2xl border border-line bg-surface overflow-hidden soft h-full flex flex-col">
      {/* scallop canopy (Midjourney) */}
      <div className="h-12 flex-none bg-cover" style={{ backgroundImage: "linear-gradient(to bottom, rgba(251,249,244,0) 35%, #FBF9F4 100%), url('/assets/marquee-scallop.jpg')", backgroundPosition: 'center 28%' }} />
      <div className="px-4 py-3 border-b border-line flex items-center gap-3 -mt-2">
        <div className="h-9 w-9 rounded-full grid place-items-center text-surface font-semibold" style={{ background: '#CC785C' }}>S</div>
        <div>
          <div className="text-[14px] font-medium leading-none">Sai</div>
          <div className="text-[11px] text-inkSoft leading-none mt-1">your event planner</div>
        </div>
        <span className="bulbs ml-auto"><i /><i /><i /></span>
      </div>
      <div ref={threadRef} className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={'fade-in flex ' + (m.from === 'user' ? 'justify-end' : 'justify-start')}>
            <div
              className="max-w-[80%] px-3.5 py-2.5 rounded-2xl text-[13.5px] whitespace-pre-line leading-relaxed"
              style={m.from === 'user'
                ? { background: '#F6E6DE', color: '#1B1A17', borderBottomRightRadius: '.35rem' }
                : { background: '#FBF9F4', color: '#1B1A17', border: '1px solid #E5DFD2', borderBottomLeftRadius: '.35rem' }}
            >{m.text}</div>
          </div>
        ))}
      </div>
      <div className="px-4 py-3 border-t border-line min-h-[60px] flex flex-wrap gap-2 items-center flex-none">
        {pendingActions
          ? pendingActions.map((a) => (
            <button key={a.label} onClick={() => onAnswer(a)} className="px-3.5 py-2 rounded-full text-[13px] font-medium"
              style={a.kind === 'primary' ? { background: '#B05E40', color: '#FBF9F4' }
                : a.kind === 'danger' ? { background: '#B2553B', color: '#FBF9F4' }
                : { background: 'transparent', color: '#6E6A63', border: '1px solid #D9D2C4' }}>{a.label}</button>
          ))
          : <input disabled placeholder="Message Sai…" className="w-full bg-surface2 border border-line rounded-full px-4 py-2 text-[13px] text-inkSoft placeholder:text-inkSoft/60" />}
      </div>
    </div>
  )
}
