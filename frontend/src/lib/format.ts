/** Formatting helpers. Everything displayed is UTC. */

export function fmtUtc(iso: string, withYear = true): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  const date = `${withYear ? d.getUTCFullYear() + '-' : ''}${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`
  return `${date} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

export function fmtHours(h: number | null | undefined): string {
  if (h === null || h === undefined || Number.isNaN(h)) return '—'
  if (h < 1) return `${Math.round(h * 60)} min`
  if (h < 48) return `${h.toFixed(1)} h`
  const total = Math.round(h)
  const d = Math.floor(total / 24)
  return `${d} d ${total - d * 24} h`
}

export function fmtDeg(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${v.toFixed(digits)}°`
}

export function fmtLat(lat: number): string {
  return `${Math.abs(lat).toFixed(3)}° ${lat < 0 ? 'S' : 'N'}`
}

export function fmtLon(lon: number): string {
  return `${Math.abs(lon).toFixed(3)}° ${lon < 0 ? 'W' : 'E'}`
}

export function fmtMetric(value: number | null, unit: string): string {
  if (value === null) return '—'
  if (unit === 'h') return fmtHours(value)
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 'deg') return fmtDeg(value)
  return `${value.toFixed(2)} ${unit}`
}

export function fmtSigned(value: number | null, unit: string): string {
  if (value === null) return '—'
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±'
  const a = Math.abs(value)
  if (unit === 'h') return `${sign}${a.toFixed(1)} h`
  if (unit === '%') return `${sign}${a.toFixed(1)} pts`
  if (unit === 'deg') return `${sign}${a.toFixed(2)}°`
  return `${sign}${a.toFixed(2)}`
}

/** "2026-12-01T12:00:00Z" -> "1 Dec" (UTC, no year). */
export function fmtDayMonth(iso: string): string {
  const d = new Date(iso)
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${d.getUTCDate()} ${months[d.getUTCMonth()]}`
}

/** "2027-01-15T12:00:00Z" <-> value for <input type="datetime-local"> treated as UTC. */
export function isoToInput(iso: string): string {
  return iso.slice(0, 16)
}
export function inputToIso(v: string): string {
  return v.length === 16 ? `${v}:00Z` : v
}
