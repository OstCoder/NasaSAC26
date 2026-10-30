import { cn } from '@/lib/utils'
import { fmtHours, fmtUtc } from '@/lib/format'
import type { Interval, IntervalSet } from '@/types/api'

export interface BandRow {
  key: keyof IntervalSet
  label: string
  barClass: string
}

export const DEFAULT_ROWS: BandRow[] = [
  { key: 'sun_visible', label: 'Sun', barClass: 'bg-sun' },
  { key: 'earth_visible', label: 'Earth', barClass: 'bg-earth' },
  { key: 'both_visible', label: 'Both', barClass: 'bg-both' },
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
              role={onPick ? 'presentation' : undefined}
            >
              {list.map((iv) => (
                <div
                  key={iv.start_utc}
                  className={cn('absolute inset-y-0', row.barClass)}
                  style={pos(iv)}
                  title={`${row.label}: ${fmtUtc(iv.start_utc)} to ${fmtUtc(iv.end_utc)} UTC (${fmtHours(iv.duration_hours)})`}
                />
              ))}
              {cursorFrac !== undefined && (
                <div className="absolute inset-y-0 w-0.5 bg-signal" style={{ left: `${cursorFrac * 100}%` }} />
              )}
            </div>
            <span className="num w-16 shrink-0 text-right text-xs text-muted">{fmtHours(total)}</span>
          </div>
        )
      })}
    </div>
  )
}
