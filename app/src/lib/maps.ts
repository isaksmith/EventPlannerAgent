// Keyless Google Maps helpers — mirror backend app/integrations/site_template.py
// so the dashboard map card and generated sites resolve the same place.

const NON_MAPPABLE = new Set([
  '',
  'tbd',
  'location tbd',
  'in person',
  'in-person',
  'virtual',
  'online',
  'remote',
  'hybrid',
])

/** Strip format qualifiers (e.g. "· in person") so the query is a real place. */
export function cleanLocationQuery(location: string): string {
  return location
    .split(/[·•|]+/)
    .map((p) => p.trim())
    .filter((p) => p && !NON_MAPPABLE.has(p.toLowerCase()))
    .join(', ')
    .trim()
}

export function isMappableLocation(location?: string | null): boolean {
  if (!location) return false
  return cleanLocationQuery(location).length > 0
}

export function mapEmbedUrl(location: string): string {
  return `https://www.google.com/maps?q=${encodeURIComponent(cleanLocationQuery(location))}&output=embed&z=17`
}

export function mapDirectionsUrl(location: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(cleanLocationQuery(location))}`
}
