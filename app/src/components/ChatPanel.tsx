import { useEffect, useRef, useState } from 'react'
import type { ChatMessage, ChatAction } from '../types'

export function ChatPanel({
  messages,
  pendingActions,
  onAnswer,
  live = false,
  onSend,
  sending = false,
}: {
  messages: ChatMessage[]
  pendingActions: ChatAction[] | null
  onAnswer: (a: ChatAction) => void
  live?: boolean
  onSend?: (text: string) => void
  sending?: boolean
}) {
  const threadRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState('')

  useEffect(() => {
    const el = threadRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length, pendingActions, sending])

  useEffect(() => {
    if (!live || pendingActions || sending) return
    inputRef.current?.focus()
  }, [live, pendingActions, sending, messages.length])

  function submitLive(e: React.FormEvent) {
    e.preventDefault()
    if (!onSend || !draft.trim() || sending) return
    onSend(draft.trim())
    setDraft('')
    requestAnimationFrame(() => inputRef.current?.focus())
  }

  return (
    <div className="rounded-2xl border border-line bg-surface overflow-hidden soft h-full flex flex-col">
      <div className="px-4 py-3 border-b border-line flex items-center gap-3">
        <div className="h-9 w-9 rounded-full grid place-items-center text-surface font-semibold" style={{ background: '#CC785C' }}>M</div>
        <div>
          <div className="text-[14px] font-medium leading-none">Marquee</div>
          <div className="text-[11px] text-inkSoft leading-none mt-1">{live ? 'live · connected' : 'your event planner'}</div>
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
          : live
            ? (
              <form onSubmit={submitLive} className="flex gap-2 w-full">
                <input
                  ref={inputRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={sending}
                  autoFocus
                  placeholder={sending ? 'Marquee is working…' : 'Type PLAN to start…'}
                  className="flex-1 bg-surface2 border border-line rounded-full px-4 py-2 text-[13px] text-ink placeholder:text-inkSoft/60"
                />
                <button type="submit" disabled={sending || !draft.trim()} className="px-4 py-2 rounded-full text-[13px] font-medium text-surface disabled:opacity-40" style={{ background: '#B05E40' }}>Send</button>
              </form>
            )
            : <input disabled placeholder="Message Marquee…" className="w-full bg-surface2 border border-line rounded-full px-4 py-2 text-[13px] text-inkSoft placeholder:text-inkSoft/60" />}
      </div>
    </div>
  )
}
