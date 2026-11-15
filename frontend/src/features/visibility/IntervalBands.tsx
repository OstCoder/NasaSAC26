import { cn } from '@/lib/utils'
import { fmtHours, fmtUtc } from '@/lib/format'
import type { Interval, IntervalSet } from '@/types/api'

export interface BandRow {
  key: keyof IntervalSet
  label: string
  barClass: string
  tone: string
}

export const DEFAULT_ROWS: BandRow[] = [
  { key: 'sun_visible', label: 'Sun', barClass: 'bg-sun', tone: 'text-sun' },
  { key: 'earth_visible', label: 'Earth', barClass: 'bg-earth', tone: 'text-earth' },
  { key: 'both_visible', label: 'Both', barClass: 'bg-both', tone: 'text-both' },
]

/**
 * Horizontal interval bands over a time window. Visible spans are solid; the
 * hatched background is "blocked" (below terrain or geometric horizon).
 * `cursorFrac` (0-1) draws the inspection cursor shared with the chart.
 */
export function IntervalBands({
  intervals,
  windowStart,
  windowEnd,
  rows = DEFAULT_ROWS,
  cursorFrac,
  onPick,
  compact = false,
  labelWidth = 'w-14',
}: {
  intervals: IntervalSet
  windowStart: string
  windowEnd: string
  rows?: BandRow[]
  cursorFrac?: number
  onPick?: (frac: number) => void
  compact?: boolean
  labelWidth?: string
}) {
  const t0 = Date.parse(windowStart)
  const span = Date.parse(windowEnd) - t0
  const cursorTime = cursorFrac === undefined ? null : t0 + cursorFrac * span
  const pos = (iv: Interval) => ({
    left: `${((Date.parse(iv.start_utc) - t0) / span) * 100}%`,
    width: `${Math.max(((Date.parse(iv.end_utc) - Date.parse(iv.start_utc)) / span) * 100, 0.15)}%`,
  })

  return (
    <div className="space-y-1.5">
      {rows.map((row) => {
        const list = intervals[row.key]
        const total = list.reduce((a, b) => a + b.duration_hours, 0)
        return (
          <div key={row.key} className="flex items-center gap-2">
            <span className={cn('shrink-0 text-xs text-muted', labelWidth)}>{row.label}</span>
            <div
              className={cn(
                'hatch-blocked relative flex-1 overflow-hidden rounded-sm bg-night',
                compact ? 'h-3' : 'h-5',
                onPick && 'cursor-pointer',
              )}
              onClick={(e) => {
                if (!onPick) return
                const r = e.currentTarget.getBoundingClientRect()
                onPick((e.clientX - r.left) / r.width)
              }}
              onKeyDown={(e) => {
                if (!onPick || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return
                e.preventDefault()
                const step = e.key === 'ArrowRight' ? 0.01 : -0.01
                onPick(Math.max(0, Math.min(1, (cursorFrac ?? 0) + step)))
              }}
              role={onPick ? 'button' : undefined}
              tabIndex={onPick ? 0 : undefined}
              aria-label={
                onPick
                  ? `${row.label} visibility bands over the mission. Total visible ${fmtHours(total)}. Use left and right arrows to move the inspected time.`
                  : undefined
              }
            >
              {list.map((iv) => {
                const active =
                  cursorTime !== null &&
                  cursorTime >= Date.parse(iv.start_utc) &&
                  cursorTime <= Date.parse(iv.end_utc)
                return (
                  <div
                    key={iv.start_utc}
                    className={cn(
                      'absolute inset-y-0',
                      row.barClass,
                      active && 'z-10 ring-1 ring-signal ring-inset',
                    )}
                    style={pos(iv)}
                    aria-current={active ? 'time' : undefined}
                    title={`${row.label}: ${fmtUtc(iv.start_utc)} to ${fmtUtc(iv.end_utc)} UTC (${fmtHours(iv.duration_hours)})`}
                  />
                )
              })}
              {cursorFrac !== undefined && (
                <div className="absolute inset-y-0 w-0.5 bg-signal" style={{ left: `${cursorFrac * 100}%` }} />
              )}
            </div>
            <span
              className={cn(
                'num w-16 shrink-0 text-right text-sm font-semibold rounded-md px-1.5 py-0.5',
                row.tone === 'text-sun' ? 'bg-sun/15 text-sun' :
                row.tone === 'text-earth' ? 'bg-earth/15 text-earth' :
                row.tone === 'text-both' ? 'bg-both/15 text-both' :
                'bg-raised text-muted',
              )}
            >
              {fmtHours(total)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
