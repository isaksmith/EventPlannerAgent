import { useEffect, useReducer, useRef, useState } from 'react'
import { deleteSession, fetchSession, fetchTraces, postPoke, setApiBase, apiBase } from '../api/client'
import type { ChatAction } from '../types'
import { applyProfileToState, profileFromApi, spansFromTraces } from './liveSync'
import type { Orchestrator, OrchestratorState } from './useOrchestrator'
import { initialOrchestratorState } from './useOrchestrator'

export function useLiveOrchestrator(enabled: boolean): Orchestrator & { send: (text: string) => Promise<void>; sending: boolean } {
  const ref = useRef<OrchestratorState>(initialOrchestratorState())
  const [sending, setSending] = useState(false)
  const [, force] = useReducer((x) => x + 1, 0)

  async function syncFromBackend() {
    const raw = await fetchSession()
    if (!raw) return
    applyProfileToState(ref.current, profileFromApi(raw), apiBase())
    try {
      const traces = await fetchTraces()
      ref.current.spans = spansFromTraces(traces)
    } catch {
      /* traces optional */
    }
    force()
  }

  useEffect(() => {
    if (!enabled) return
    let timer: ReturnType<typeof setInterval> | undefined
    const poll = () => {
      void syncFromBackend().catch(() => {})
    }
    poll()
    timer = setInterval(poll, 2500)
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [enabled])

  async function send(text: string) {
    const body = text.trim()
    if (!body || sending) return
    setSending(true)
    const st = ref.current
    st.pendingActions = null
    st.waiting = false
    st.messages = [...st.messages, { from: 'user', text: body }]
    force()

    try {
      const replies = await postPoke(body)
      for (const reply of replies) {
        st.messages = [...st.messages, { from: 'sai', text: reply }]
        force()
      }
      await syncFromBackend()
    } catch (err) {
      st.messages = [
        ...st.messages,
        {
          from: 'sai',
          text: `Could not reach the backend.\nStart uvicorn on port 8000.\n\n${(err as Error).message}`,
        },
      ]
      force()
    } finally {
      setSending(false)
      force()
    }
  }

  function answer(action: ChatAction) {
    void send(action.reply)
  }

  function reset() {
    void deleteSession().catch(() => {})
    ref.current = initialOrchestratorState()
    ref.current.messages = [
      { from: 'sai', text: "Hi — I'm Marquee, your event planner. Type PLAN to start, or use Auto-play for the demo." },
    ]
    force()
  }

  // bootstrap hint
  if (ref.current.messages.length === 0) {
    ref.current.messages = [
      { from: 'sai', text: "Hi — I'm Marquee, your event planner. Type PLAN to start, or use Auto-play for the demo." },
    ]
  }

  return {
    state: ref.current,
    next: () => {},
    answer,
    toggleAuto: () => {},
    reset,
    togglePanel: (key) => {
      const st = ref.current
      st.openPanels = st.openPanels.includes(key)
        ? st.openPanels.filter((k) => k !== key)
        : [...st.openPanels, key]
      force()
    },
    send,
    sending,
  }
}
