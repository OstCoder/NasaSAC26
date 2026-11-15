import type { IntervalSet } from '@/types/api'

export interface NextTransition {
  time: number
  body: 'sun' | 'earth'
  kind: 'rise' | 'set'
  label: string
}

/** The first modelled visibility edge strictly after `after` (epoch ms). */
export function nextTransition(intervals: IntervalSet, after: number): NextTransition | null {
  const candidates: NextTransition[] = []
  const add = (body: 'sun' | 'earth', kind: 'rise' | 'set', iso: string) => {
    const time = Date.parse(iso)
    if (Number.isFinite(time) && time > after + 1) {
      const name = body === 'sun' ? (kind === 'rise' ? 'Sunrise' : 'Sunset') : (kind === 'rise' ? 'Earthrise' : 'Earthset')
      candidates.push({ time, body, kind, label: name })
    }
  }
  for (const interval of intervals.sun_visible) {
    add('sun', 'rise', interval.start_utc)
    add('sun', 'set', interval.end_utc)
  }
  for (const interval of intervals.earth_visible) {
    add('earth', 'rise', interval.start_utc)
    add('earth', 'set', interval.end_utc)
  }
  candidates.sort((a, b) => a.time - b.time)
  return candidates[0] ?? null
}

/** View-only time domain for the visibility chart. */
export function zoomDomain(
  windowStart: number,
  windowEnd: number,
  cursor: number,
  zoomHours: number | null,
): [number, number] {
  if (!(windowEnd > windowStart)) return [windowStart, windowEnd]
  const span = zoomHours === null ? 0 : zoomHours * 3_600_000
  if (span <= 0 || span >= windowEnd - windowStart) return [windowStart, windowEnd]

  // Keep the inspected sample in view, then pull the window back inside the
  // mission so an edge sample never produces an out-of-range domain.
  const centre = Math.min(windowEnd, Math.max(windowStart, cursor))
  const start = Math.max(windowStart, centre - span / 2)
  const end = Math.min(windowEnd, start + span)
  return [Math.max(windowStart, end - span), end]
}
