import { useEffect, useRef, useState } from 'react'
import { assetUrl, backendUrl, deleteEvent, fetchEvent, fetchEvents, type PastEvent } from '../api/client'
import { Icon } from './Icon'

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function EventRow({ ev, onDelete, onView }: { ev: PastEvent; onDelete: (id: string) => void; onView: (ev: PastEvent) => void }) {
  const [open, setOpen] = useState(false)
  const subtitle = [ev.type, ev.location].filter(Boolean).join(' · ')
  return (
    <li className="rounded-lg border border-line bg-surface overflow-hidden">
      <div className="flex items-center gap-3 p-2">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-3 flex-1 min-w-0 text-left"
          aria-expanded={open}
        >
          <div className="h-10 w-10 shrink-0 rounded-md border border-line overflow-hidden bg-surface2 grid place-items-center">
            {ev.cover_url ? (
              <img src={assetUrl(ev.cover_url)} alt="" className="w-full h-full object-cover" />
            ) : (
              <Icon name="image" size={16} style={{ color: ev.colors[0] || '#B05E40' }} />
            )}
          </div>
          <div className="min-w-0">
            <div className="text-[12px] font-medium text-ink truncate">{ev.name}</div>
            <div className="text-[10px] text-inkSoft truncate">
              {subtitle || 'event'} · {formatDate(ev.created_at)}
            </div>
          </div>
        </button>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => onView(ev)}
            className="text-[10px] px-2 py-1 rounded-md text-surface font-medium hover:brightness-110 inline-flex items-center gap-1"
            style={{ background: '#B05E40' }}
            title="View event dashboard"
          >
            Dashboard <Icon name="externalLink" size={11} />
          </button>
          {ev.site_url && (
            <a
              href={backendUrl(ev.site_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] px-2 py-1 rounded-md border border-line text-inkSoft hover:bg-surface2 inline-flex items-center gap-1"
              title="View generated site"
            >
              Site <Icon name="externalLink" size={11} />
            </a>
          )}
          <button
            type="button"
            onClick={() => onDelete(ev.id)}
            className="grid place-items-center h-6 w-6 rounded-md border border-line text-inkSoft hover:bg-surface2 hover:text-ink"
            title="Remove from history"
            aria-label="Remove from history"
          >
            <Icon name="x" size={13} />
          </button>
        </div>
      </div>
      {open && (
        <div className="px-2 pb-2 pt-1 border-t border-line">
          {ev.colors.length > 0 && (
            <div className="flex items-center gap-1.5 mb-2">
              {ev.colors.slice(0, 6).map((c, i) => (
                <span
                  key={i}
                  className="h-3.5 w-3.5 rounded-full border border-line"
                  style={{ background: c }}
                  title={c}
                />
              ))}
              {ev.vibe && <span className="text-[10px] text-inkSoft ml-1 truncate">{ev.vibe}</span>}
            </div>
          )}
          {ev.brand_files.length > 0 ? (
            <div className="grid grid-cols-4 gap-1.5">
              {ev.brand_files.map((f) => (
                <div key={f.name} className="rounded-md border border-line overflow-hidden bg-surface2 aspect-square">
                  <img src={assetUrl(f.url)} alt={f.name} className="w-full h-full object-cover" />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[10px] text-inkSoft">No brand assets saved.</div>
          )}
        </div>
      )}
    </li>
  )
}

export function PastEvents({ onViewEvent }: { onViewEvent?: (ev: PastEvent) => void }) {
  const [open, setOpen] = useState(false)
  const [events, setEvents] = useState<PastEvent[]>([])
  const [loading, setLoading] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  async function load() {
    setLoading(true)
    try {
      setEvents(await fetchEvents())
    } catch {
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) void load()
  }, [open])

  useEffect(() => {
    if (!open) return
    function onClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    window.addEventListener('mousedown', onClick)
    return () => window.removeEventListener('mousedown', onClick)
  }, [open])

  async function handleDelete(id: string) {
    setEvents((prev) => prev.filter((e) => e.id !== id))
    try {
      await deleteEvent(id)
    } catch {
      void load()
    }
  }

  return (
    <div className="relative" ref={wrapRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={
          'px-3 py-1.5 rounded-lg text-sm border flex items-center gap-1.5 transition-colors ' +
          (open ? 'border-clay/50 text-clay bg-clay/10' : 'border-line text-inkSoft hover:bg-surface2')
        }
        aria-expanded={open}
        title="Browse previously generated events"
      >
        <Icon name="folder" size={15} /> Past events
        {events.length > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface2 border border-line text-inkSoft">
            {events.length}
          </span>
        )}
        <Icon name="chevronDown" size={14} className={'transition-transform ' + (open ? 'rotate-180' : '')} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-[360px] max-w-[92vw] max-h-[70vh] overflow-y-auto rounded-xl border border-line bg-canvas shadow-xl z-50">
          <div className="sticky top-0 bg-canvas/95 backdrop-blur px-3 py-2.5 border-b border-line flex items-center justify-between">
            <div className="text-[13px] font-semibold">Previously generated events</div>
            <button
              type="button"
              onClick={() => void load()}
              className="grid place-items-center h-6 w-6 rounded-md border border-line text-inkSoft hover:bg-surface2 hover:text-ink"
              title="Refresh"
              aria-label="Refresh"
            >
              <Icon name="refresh" size={13} />
            </button>
          </div>
          <div className="p-2.5">
            {loading ? (
              <div className="text-[11px] text-inkSoft py-6 text-center">Loading…</div>
            ) : events.length === 0 ? (
              <div className="text-[11px] text-inkSoft py-6 text-center">
                No past events yet. Plan an event, then start a new one — finished events are saved here.
              </div>
            ) : (
              <ul className="space-y-2">
                {events.map((ev) => (
                  <EventRow key={ev.id} ev={ev} onDelete={handleDelete} onView={(e) => onViewEvent?.(e)} />
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
