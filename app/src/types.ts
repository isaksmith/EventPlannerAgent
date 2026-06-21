// Shared domain types used across the UI and the integration seams.

export type Phase = 0 | 1 | 2 | 3 | 4 | 5
export type ProfileStatus =
  | 'interviewing'
  | 'awaiting_approval'
  | 'executing'
  | 'awaiting_handoff'
  | 'done'

export interface EventProfile {
  session_id: string
  status: ProfileStatus
  event: { name?: string; type?: string; location?: string; expected_attendees?: number }
  audience: { description?: string }
  aesthetic: { vibe?: string }
  ops: { needs_slack?: boolean; needs_devpost?: boolean }
  outreach: { sponsor_targets?: string[] }
  artifacts: { site_url?: string }
}

export type DeliverableKey = 'branding' | 'website' | 'outreach'

export interface ChatAction { label: string; reply: string; kind: 'primary' | 'danger' | 'line' }
export interface ChatMessage { from: 'sai' | 'user'; text: string }

export interface ArizeSpan { node: string; ms: number; cost: number; warn?: boolean }

// ---- Deliverable payloads (what the integrations produce) ----
export interface BrandPalette { hex: string; name: string }
export interface BrandAssetPreview { label: string; glyph: string }
export interface BrandKit {
  vibe: string
  logo: { text: string; accent: string; bg: string }
  palette: BrandPalette[]
  assets: BrandAssetPreview[]
}

export interface SiteResult { url: string; eyebrow: string; title: string; subtitle: string }

export interface SlackResult { ok: boolean; channels?: string[]; fallback?: string }
export interface DevpostResult { ok: boolean; url?: string; fallback?: string }

export interface EmailDraft { to: string; subject: string; body: string }
