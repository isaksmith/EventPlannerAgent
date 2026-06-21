// Deliverable tiles (Branding / Website / Outreach), the tiling grid, and the
// maximize modal. Tile bodies render purely from integration-produced data.
import type { DeliverableKey, BrandKit, SiteResult, EmailDraft, LocationInfo } from '../types'
import { Icon, type IconName } from './Icon'
import { mapDirectionsUrl, mapEmbedUrl } from '../lib/maps'

export interface Deliverables { branding?: BrandKit; website?: SiteResult; location?: LocationInfo; outreach?: EmailDraft[] }
export const ORDER: DeliverableKey[] = ['branding', 'website', 'location', 'outreach']
export const META: Record<DeliverableKey, { icon: IconName; label: string; title: string }> = {
  branding: { icon: 'palette', label: 'Branding', title: 'Brand' },
  website: { icon: 'globe', label: 'Website', title: 'Website' },
  location: { icon: 'mapPin', label: 'Location', title: 'Location' },
  outreach: { icon: 'mail', label: 'Outreach', title: 'Outreach' },
}

function TileTitle({ k }: { k: DeliverableKey }) {
  return (
    <span className="text-sm font-semibold flex items-center gap-2">
      <Icon name={META[k].icon} size={15} className="text-clay" />
      {META[k].title}
    </span>
  )
}

function Swatches({ palette, big }: { palette: BrandKit['palette']; big?: boolean }) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {palette.map((c) => (
        <div key={c.hex}>
          <div className="swatch" style={{ background: c.hex, height: big ? 52 : undefined }} />
          {big && (<><div className="mono text-[10px] text-clay mt-1">{c.hex}</div><div className="text-[10px] text-inkSoft">{c.name}</div></>)}
        </div>
      ))}
    </div>
  )
}

function SiteFrame({ site }: { site: SiteResult }) {
  return (
    <div className="rounded-lg border border-line overflow-hidden bg-white relative h-full min-h-[120px]">
      <div className="absolute inset-x-0 top-0 h-5 bg-slate-200 flex items-center gap-1 px-2 z-10">
        <span className="h-2 w-2 rounded-full" style={{ background: '#B2553B' }} />
        <span className="h-2 w-2 rounded-full" style={{ background: '#BC8A2E' }} />
        <span className="h-2 w-2 rounded-full" style={{ background: '#7E8C57' }} />
        <span className="ml-2 text-[9px] text-slate-500 mono truncate">{site.loading ? '…' : site.url}</span>
      </div>
      {site.loading ? (
        <div className="absolute inset-0 top-5 flex flex-col items-center justify-center gap-3 px-3 animate-pulse" style={{ background: 'linear-gradient(135deg,#141822,#0d1117)' }}>
          <div style={{ color: 'rgba(34,211,238,.45)' }}>
            <div className="h-3 w-24 rounded mx-auto mb-3" style={{ background: 'rgba(34,211,238,.15)' }} />
            <div className="h-5 w-32 rounded mx-auto mb-2" style={{ background: 'rgba(34,211,238,.1)' }} />
            <div className="h-2.5 w-40 rounded mx-auto mb-4" style={{ background: 'rgba(34,211,238,.08)' }} />
            <div className="h-6 w-20 rounded-full mx-auto" style={{ background: 'rgba(34,211,238,.12)' }} />
          </div>
          <div className="text-[10px]" style={{ color: 'rgba(34,211,238,.6)' }}>
            Building site…
          </div>
        </div>
      ) : (
        <div className="absolute inset-0 top-5 text-white" style={{ background: 'linear-gradient(135deg,#0a1f44,#08111f)' }}>
          <div className="h-full flex flex-col items-center justify-center text-center px-3 scanline">
            <div className="text-[8px] tracking-[0.3em]" style={{ color: 'rgba(127,211,224,.85)' }}>{site.eyebrow}</div>
            <div className="text-[clamp(14px,2.4vw,26px)] font-bold mt-1">{site.title}</div>
            <div className="text-[10px] text-slate-300 mt-1">{site.subtitle}</div>
            <button className="mt-2.5 text-[10px] font-semibold px-3 py-1 rounded-full" style={{ background: '#22d3ee', color: '#0a1f44' }}>Register →</button>
          </div>
        </div>
      )}
    </div>
  )
}

function MapCard({ loc, full }: { loc: LocationInfo; full?: boolean }) {
  return (
    <div className={'rounded-lg border border-line overflow-hidden bg-surface2 ' + (full ? '' : 'h-full')}>
      <iframe
        title={`Map showing ${loc.query}`}
        src={mapEmbedUrl(loc.query)}
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        className="w-full block border-0"
        style={{ height: full ? '46vh' : '100%', minHeight: full ? 280 : 120 }}
        allowFullScreen
      />
    </div>
  )
}

function AssetTile({ label, glyph, imageUrl, videoUrl }: { label: string; glyph?: string; imageUrl?: string; videoUrl?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface2 overflow-hidden">
      <div className="h-full overflow-hidden scanline" style={{ minHeight: 64 }}>
        {videoUrl ? (
          <video src={videoUrl} className="w-full h-full object-cover" muted loop playsInline autoPlay />
        ) : imageUrl ? (
          <img src={imageUrl} alt={label} className="w-full h-full object-cover" />
        ) : (
          <div className="h-full grid place-items-center text-[10px]" style={{ background: 'linear-gradient(120deg,#0a1f44,#08111f)', minHeight: 64, color: 'rgba(34,211,238,.7)' }}>{glyph || '◆'}</div>
        )}
      </div>
      <div className="text-[10px] text-inkSoft px-2 py-1 border-t border-line">{label}</div>
    </div>
  )
}

function LogoMark({ kit, size }: { kit: BrandKit; size: 'sm' | 'lg' }) {
  const dim = size === 'lg' ? 'h-24 w-24' : 'h-14 w-14'
  const textSize = size === 'lg' ? 'text-3xl' : 'text-sm'
  if (kit.logo.imageUrl) {
    return <img src={kit.logo.imageUrl} alt="Logo" className={`${dim} shrink-0 rounded-xl border border-line object-cover`} />
  }
  return (
    <div className={`${dim} shrink-0 rounded-xl border border-line flex items-center justify-center font-bold ${textSize}`} style={{ background: kit.logo.bg, color: '#22d3ee' }}>
      <span className="whitespace-nowrap">{kit.logo.text.slice(0, 2)}<span style={{ color: kit.logo.accent }}>/</span>{kit.logo.text.slice(2, 4) || 'EV'}</span>
    </div>
  )
}

function BrandSource({ kit }: { kit: BrandKit }) {
  if (kit.generatedBy === 'loading') {
    return (
      <div className="text-[10px] text-clay flex items-center gap-1.5">
        Generating brand assets…
      </div>
    )
  }
  const source = kit.generatedBy === 'openrouter' || kit.generatedBy === 'midjourney' ? 'OpenRouter' : 'Generated assets'
  const count = kit.assets.length + (kit.logo.imageUrl ? 1 : 0) + (kit.heroImageUrl ? 1 : 0) + (kit.promoVideoUrl ? 1 : 0)
  return <div className="text-[10px] text-inkSoft">{count} assets · {source} · {kit.vibe}</div>
}

export function TileBody({ k, deliverables, full }: { k: DeliverableKey; deliverables: Deliverables; full?: boolean }) {
  if (k === 'branding') {
    const kit = deliverables.branding
    if (!kit) return null
    if (!full) return (
      <div className="p-3 space-y-3 h-full flex flex-col">
        <div className="flex gap-3 items-center">
          <LogoMark kit={kit} size="sm" />
          <div className="flex-1"><Swatches palette={kit.palette} /></div>
        </div>
        <div className="rounded-lg border border-line overflow-hidden flex-1 min-h-[48px]">
          {kit.generatedBy === 'loading' ? (
            <div className="h-full animate-pulse" style={{ background: 'linear-gradient(120deg,#1a1e2b,#121520)' }}>
              <div className="h-full flex flex-col items-center justify-center gap-2">
                <div className="h-2.5 w-28 rounded" style={{ background: 'rgba(34,211,238,.12)' }} />
                <div className="h-3 w-36 rounded" style={{ background: 'rgba(34,211,238,.08)' }} />
              </div>
            </div>
          ) : kit.heroImageUrl ? (
            <img src={kit.heroImageUrl} alt="Hero" className="w-full h-full object-cover min-h-[48px]" />
          ) : (
            <div className="h-full grid place-items-center text-[10px]" style={{ background: 'linear-gradient(120deg,#0a1f44,#08111f)', color: 'rgba(34,211,238,.7)' }}>◢◤ background graphic</div>
          )}
        </div>
        <BrandSource kit={kit} />
      </div>
    )
    return (
      <div className="space-y-5">
        <div className="flex gap-4 items-center">
          <LogoMark kit={kit} size="lg" />
            <div>
            <div className="text-lg font-semibold">{kit.vibe || 'Brand kit'}</div>
            <div className="text-inkSoft text-sm">
              {kit.generatedBy === 'midjourney'
                ? 'Invite visuals generated by Midjourney from your theme'
                : 'Brand assets ready'}
            </div>
          </div>
        </div>
        {!kit.heroImageUrl && kit.generatedBy === 'loading' ? (
          <div>
            <div className="text-sm font-semibold mb-2">Invite cover</div>
            <div className="rounded-xl border border-line overflow-hidden animate-pulse" style={{ background: 'linear-gradient(120deg,#1a1e2b,#121520)', height: 200 }}>
              <div className="h-full flex flex-col items-center justify-center gap-2">
                <div className="h-4 w-40 rounded" style={{ background: 'rgba(34,211,238,.1)' }} />
                <div className="h-3 w-32 rounded" style={{ background: 'rgba(34,211,238,.07)' }} />
              </div>
            </div>
          </div>
        ) : kit.heroImageUrl && (
          <div>
            <div className="text-sm font-semibold mb-2">Invite cover</div>
            <img src={kit.heroImageUrl} alt="Invite cover" className="w-full max-h-48 rounded-xl border border-line object-cover" />
          </div>
        )}
        {kit.promoVideoUrl && (
          <div>
            <div className="text-sm font-semibold mb-2">Promo clip</div>
            <video src={kit.promoVideoUrl} className="w-full max-h-48 rounded-xl border border-line object-cover" controls muted loop playsInline />
          </div>
        )}
        <div><div className="text-sm font-semibold mb-2">Color palette</div><Swatches palette={kit.palette} big /></div>
        {kit.assets.length > 0 && (
          <div>
            <div className="text-sm font-semibold mb-2">Brand assets</div>
            <div className="grid grid-cols-3 gap-3" style={{ gridAutoRows: '110px' }}>
              {kit.assets.map((a) => <AssetTile key={a.label} label={a.label} glyph={a.glyph} imageUrl={a.imageUrl} videoUrl={a.videoUrl} />)}
            </div>
          </div>
        )}
      </div>
    )
  }

  if (k === 'website') {
    const site = deliverables.website
    if (!site) return null
    if (!full) return (
      <div className="p-3 h-full flex flex-col gap-2">
        <div className="flex-1 min-h-0"><SiteFrame site={site} /></div>
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-inkSoft">{site.loading ? 'Generating registration site…' : 'Live registration site'}</span>
          {!site.loading && (
            <a
              href={`https://${site.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] px-2.5 py-1 rounded-md text-surface font-medium hover:brightness-110 inline-flex items-center gap-1"
              style={{ background: '#B05E40' }}
            >
              View Live Site <Icon name="externalLink" size={11} />
            </a>
          )}
        </div>
      </div>
    )
    return (
      <div className="space-y-4">
        <div className="h-[42vh] min-h-[260px]"><SiteFrame site={site} /></div>
        {!site.loading && (
          <>
            <div className="flex items-center gap-3">
              <a href={`https://${site.url}`} target="_blank" rel="noopener noreferrer" className="text-[12px] px-3 py-1.5 rounded-md text-surface inline-flex items-center gap-1.5 hover:brightness-110" style={{ background: '#B05E40' }}>Open site <Icon name="externalLink" size={12} /></a>
              <span className="mono text-[12px] text-clay">{site.url}</span>
            </div>
            <div className="grid grid-cols-3 gap-3 text-[12px]">
              <div className="rounded-lg border border-line bg-surface2 p-3"><div className="font-medium">Registration form</div><div className="text-inkSoft mt-1">name · email · team · track</div></div>
              <div className="rounded-lg border border-line bg-surface2 p-3"><div className="font-medium">Sections</div><div className="text-inkSoft mt-1">hero · schedule · prizes · FAQ</div></div>
              <div className="rounded-lg border border-line bg-surface2 p-3"><div className="font-medium">Deploy</div><div className="text-inkSoft mt-1">Claude Code → Vercel</div></div>
            </div>
          </>
        )}
      </div>
    )
  }

  if (k === 'location') {
    const loc = deliverables.location
    if (!loc) return null
    if (!full) return (
      <div className="p-3 h-full flex flex-col gap-2">
        <div className="flex-1 min-h-0"><MapCard loc={loc} /></div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] text-inkSoft truncate" title={loc.label}>{loc.label}</span>
          <a
            href={mapDirectionsUrl(loc.query)}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 text-[10px] px-2.5 py-1 rounded-md text-surface font-medium hover:brightness-110 inline-flex items-center gap-1"
            style={{ background: '#B05E40' }}
          >
            Directions <Icon name="navigation" size={11} />
          </a>
        </div>
      </div>
    )
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm">
          <Icon name="mapPin" size={18} className="text-clay" />
          <span className="font-semibold">{loc.label}</span>
        </div>
        <MapCard loc={loc} full />
        <a
          href={mapDirectionsUrl(loc.query)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-md text-surface hover:brightness-110"
          style={{ background: '#B05E40' }}
        >
          <Icon name="navigation" size={13} /> Get directions
        </a>
      </div>
    )
  }

  const mails = deliverables.outreach
  if (!mails) return null
  const isLoading = mails.length === 1 && mails[0].to === '…'
  if (!full) return (
    <div className="p-3 space-y-2 h-full flex flex-col">
      {isLoading ? (
        <div className="flex-1 flex flex-col gap-2 justify-center">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-lg border border-line bg-surface2 p-2 animate-pulse">
              <div className="h-3 w-3/4 rounded" style={{ background: 'rgba(176,94,64,.12)' }} />
              <div className="h-2.5 w-1/3 rounded mt-1.5" style={{ background: 'rgba(176,94,64,.07)' }} />
            </div>
          ))}
          <div className="text-[10px] text-clay flex items-center gap-1.5 mt-1">
            <span className="spinner" /> Drafting sponsor emails…
          </div>
        </div>
      ) : (
        <>
          {mails.map((e) => (
            <div key={e.to} className="rounded-lg border border-line bg-surface2 p-2">
              <div className="text-[12px] truncate">{e.subject}</div>
              <div className="text-[10px] text-inkSoft truncate">{e.to}</div>
            </div>
          ))}
        </>
      )}
      <div className="text-[10px] mt-auto rounded p-1.5" style={{ color: '#8f3f28', background: 'rgba(178,85,59,.08)', border: '1px solid rgba(178,85,59,.25)' }}>Drafts only — approve in chat to send.</div>
    </div>
  )
  return (
    <div className="space-y-3">
      {isLoading ? (
        <div className="rounded-xl border border-line bg-surface2 p-6 flex flex-col items-center gap-3">
          <div className="animate-pulse space-y-3 w-full max-w-xs">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border border-line bg-surface p-3">
                <div className="h-3.5 w-2/3 rounded mb-2" style={{ background: 'rgba(176,94,64,.12)' }} />
                <div className="h-2.5 w-full rounded mb-1" style={{ background: 'rgba(176,94,64,.06)' }} />
                <div className="h-2.5 w-5/6 rounded" style={{ background: 'rgba(176,94,64,.06)' }} />
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 text-clay text-[12px]">
            <span className="spinner" /> Drafting sponsor emails…
          </div>
        </div>
      ) : (
        <>
          {mails.map((e) => (
            <div key={e.to} className="rounded-xl border border-line bg-surface2 p-4">
              <div className="flex items-center gap-2"><span className="text-sm font-medium">{e.subject}</span>
                <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded" style={{ color: '#8f3f28', background: 'rgba(178,85,59,.1)', border: '1px solid rgba(178,85,59,.3)' }}>DRAFT · awaiting your OK</span></div>
              <div className="text-[11px] text-inkSoft mt-0.5 mono">to: {e.to}</div>
              <div className="text-[12px] mt-2 whitespace-pre-line leading-relaxed">{e.body}</div>
            </div>
          ))}
        </>
      )}
      <div className="text-[12px] rounded-lg p-2.5" style={{ color: '#8f3f28', background: 'rgba(178,85,59,.08)', border: '1px solid rgba(178,85,59,.22)' }}>Nothing sends until you approve it in the chat — that's a Tier 3 human handoff.</div>
    </div>
  )
}

const PLACEHOLDER_TEXT: Record<DeliverableKey, { heading: string; body: string }> = {
  branding: { heading: 'Brand', body: 'Logo, color palette, hero image, and brand assets will appear here once your event plan is approved.' },
  website: { heading: 'Website', body: 'A live preview of your event landing page and a link to the Vercel deployment will appear here.' },
  location: { heading: 'Venue map', body: 'A Google Maps embed pinning your event location with directions will appear here.' },
  outreach: { heading: 'Sponsor outreach', body: 'Draft emails to your sponsor targets will appear here for your review before sending.' },
}

function PlaceholderTile({ k }: { k: DeliverableKey }) {
  return (
    <div className="p-4 h-full flex flex-col items-center justify-center text-center gap-3">
      <Icon name={META[k].icon} size={28} className="text-inkSoft/30" />
      <div>
        <div className="text-[13px] font-medium text-inkSoft/70">{PLACEHOLDER_TEXT[k].heading}</div>
        <div className="text-[11px] text-inkSoft/50 mt-1.5 leading-relaxed max-w-[260px]">{PLACEHOLDER_TEXT[k].body}</div>
      </div>
    </div>
  )
}

export function TileGrid({ open, deliverables, cols, onMaximize, onClose, placeholder }: {
  open: DeliverableKey[]; deliverables: Deliverables; cols: number
  onMaximize: (k: DeliverableKey) => void; onClose: (k: DeliverableKey) => void
  placeholder?: boolean
}) {
  return (
    <div className="h-full flex-1" style={{ display: 'grid', gap: 14, gridAutoRows: 'minmax(0,1fr)', gridTemplateColumns: `repeat(${cols}, minmax(0,1fr))` }}>
      {open.map((k) => (
        <div key={k} className="tile tile-in rounded-2xl border border-line bg-surface soft">
          <div className="tile-head">
            <TileTitle k={k} />
            {placeholder ? (
              <>
                <button className="tbtn ml-auto" title="Coming soon" aria-label="Coming soon" disabled><Icon name="maximize" size={14} /></button>
                <button className="tbtn" title="Coming soon" aria-label="Coming soon" disabled><Icon name="x" size={15} /></button>
              </>
            ) : (
              <>
                <button className="tbtn ml-auto" title="Maximize" aria-label="Maximize panel" onClick={() => onMaximize(k)}><Icon name="maximize" size={14} /></button>
                <button className="tbtn" title="Close" aria-label="Close panel" onClick={() => onClose(k)}><Icon name="x" size={15} /></button>
              </>
            )}
          </div>
          <div className="tile-body">
            {placeholder ? <PlaceholderTile k={k} /> : <TileBody k={k} deliverables={deliverables} />}
          </div>
        </div>
      ))}
    </div>
  )
}

export function MaximizeModal({ k, deliverables, onClose }: { k: DeliverableKey | null; deliverables: Deliverables; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[60] transition-opacity duration-200" style={{ opacity: k ? 1 : 0, pointerEvents: k ? 'auto' : 'none' }}>
      <div className="absolute inset-0" style={{ background: 'rgba(27,26,23,.45)' }} onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center p-4 md:p-8">
        <div className="relative w-full max-w-5xl h-[88vh] bg-surface border border-line rounded-2xl overflow-hidden flex flex-col soft">
          <div className="px-5 py-3 border-b border-line flex items-center gap-2 flex-none bg-surface2">
            <h3 className="text-sm font-semibold flex items-center gap-2">{k && <Icon name={META[k].icon} size={16} className="text-clay" />}{k ? META[k].title : ''}</h3>
            <button className="ml-auto grid place-items-center h-8 w-8 rounded-md border border-line text-inkSoft hover:bg-surface2 hover:text-ink" aria-label="Close" onClick={onClose}><Icon name="x" size={16} /></button>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto p-5">{k && <TileBody k={k} deliverables={deliverables} full />}</div>
        </div>
      </div>
    </div>
  )
}
