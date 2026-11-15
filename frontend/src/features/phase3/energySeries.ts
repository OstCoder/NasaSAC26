import type { PowerSeries } from '@/types/api'

export interface EnergyPoint {
  t: number
  solar: number
  load: number
  battery: number
  soc: number
  unserved: number
  sun: boolean
}

export interface BlockedSpan {
  x1: number
  x2: number
}

/**
 * Turn the aligned engineering arrays into chart rows without inventing
 * samples. If an array is short, the shortest length wins and the missing
 * values are not plotted.
 */
export function toEnergyPoints(series: PowerSeries): EnergyPoint[] {
  const n = Math.min(
    series.times_utc.length,
    series.solar_w.length,
    series.load_w.length,
    series.battery_wh.length,
    series.battery_soc_pct.length,
    series.unserved_wh.length,
    series.sun_visible.length,
  )
  const out: EnergyPoint[] = []
  for (let i = 0; i < n; i += 1) {
    const t = Date.parse(series.times_utc[i])
    if (!Number.isFinite(t)) continue
    out.push({
      t,
      solar: series.solar_w[i],
      load: series.load_w[i],
      battery: series.battery_wh[i],
      soc: series.battery_soc_pct[i],
      unserved: series.unserved_wh[i],
      sun: series.sun_visible[i],
    })
  }
  return out
}

function runSpans(times: string[], active: boolean[]): BlockedSpan[] {
  const n = Math.min(times.length, active.length)
  const spans: BlockedSpan[] = []
  let start: number | null = null

  for (let i = 0; i < n; i += 1) {
    const t = Date.parse(times[i])
    if (!Number.isFinite(t)) continue
    if (active[i] && start === null) start = t
    if (!active[i] && start !== null) {
      spans.push({ x1: start, x2: t })
      start = null
    }
  }
  if (start !== null && n > 0) {
    const end = Date.parse(times[n - 1])
    if (Number.isFinite(end)) spans.push({ x1: start, x2: Math.max(start, end) })
  }
  return spans.filter((span) => span.x2 > span.x1)
}

/** Sun-blocked runs, expressed as numeric x-axis spans for ReferenceArea. */
export function blockedSpans(series: PowerSeries): BlockedSpan[] {
  return runSpans(series.times_utc, series.sun_visible.map((visible) => !visible))
}

/** Periods where the array output exceeds the load. */
export function chargingSpans(series: PowerSeries): BlockedSpan[] {
  return runSpans(series.times_utc, series.charging)
}

/** Periods where the load exceeds the array output. */
export function dischargingSpans(series: PowerSeries): BlockedSpan[] {
  return runSpans(series.times_utc, series.discharging)
}
