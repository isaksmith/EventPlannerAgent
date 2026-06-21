const DEFAULT_API = 'http://127.0.0.1:8000'
export const DASHBOARD_PHONE = 'phone:dashboard-demo'

let configuredApi =
  (import.meta as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE || DEFAULT_API

export function setApiBase(url: string): void {
  configuredApi = url.replace(/\/$/, '') || DEFAULT_API
}

export function apiBase(): string {
  const base = configuredApi.replace(/\/$/, '') || DEFAULT_API
  // Local dashboard proxies to uvicorn — avoids ngrok/CORS failures in dev
  if (import.meta.env.DEV) {
    return ''
  }
  return base
}

/** URL shown in the Live mode header (may differ from proxied apiBase in dev). */
export function displayApiBase(): string {
  return configuredApi.replace(/\/$/, '') || DEFAULT_API
}

/** Brand images/videos — use same-origin paths in dev so img tags work (ngrok blocks direct image loads). */
export function assetUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  if (import.meta.env.DEV && normalized.startsWith('/api/assets/')) {
    return normalized
  }
  return `${apiBase()}${normalized}`
}

export async function postPoke(body: string): Promise<string[]> {
  const res = await fetch(`${apiBase()}/webhooks/poke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: DASHBOARD_PHONE, body }),
  })
  if (!res.ok) throw new Error(`Backend error ${res.status}`)
  const data = (await res.json()) as { replies?: string[] }
  return data.replies ?? []
}

export async function fetchSession(): Promise<Record<string, unknown> | null> {
  const res = await fetch(
    `${apiBase()}/api/session?phone=${encodeURIComponent(DASHBOARD_PHONE)}`,
  )
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Session fetch failed ${res.status}`)
  return res.json()
}

export async function deleteSession(): Promise<void> {
  await fetch(`${apiBase()}/api/session?phone=${encodeURIComponent(DASHBOARD_PHONE)}`, {
    method: 'DELETE',
  })
}

export async function fetchTraces(): Promise<{ name: string; latency_ms: number }[]> {
  const res = await fetch(`${apiBase()}/admin/traces`)
  if (!res.ok) return []
  const data = (await res.json()) as { spans?: { name: string; latency_ms: number }[] }
  return data.spans ?? []
}
