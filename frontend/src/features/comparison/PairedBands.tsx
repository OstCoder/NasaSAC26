import { IntervalBands } from '@/features/visibility'
import type { ScenarioResult } from '@/types/api'

/**
 * Both scenarios on a shared "time since landing" axis, so different dates line up.
 */
export function PairedBands({ a, b, aLabel, bLabel }: { a: ScenarioResult; b: ScenarioResult; aLabel: string; bLabel: string }) {
  const span = Math.max(a.duration_hours, b.duration_hours)
  const end = (r: ScenarioResult) => new Date(Date.parse(r.landing_utc) + span * 3_600_000).toISOString()
  const ticks = [0, 0.25, 0.5, 0.75, 1]
  return (
    <div className="space-y-4">
      {[{ r: a, l: aLabel }, { r: b, l: bLabel }].map(({ r, l }) => (
        <div key={l}>
          <p className="mb-1 text-[13px] font-medium text-ink">{l}</p>
          <IntervalBands intervals={r.intervals} windowStart={r.landing_utc} windowEnd={end(r)} compact labelWidth="w-14" />
        </div>
      ))}
      <div className="ml-16 mr-[72px] flex justify-between text-[11px] text-faint num">
        {ticks.map((t) => (
          <span key={t}>{t === 0 ? 'Landing' : `+${((span * t) / 24).toFixed(span > 72 ? 0 : 1)} d`}</span>
        ))}
      </div>
    </div>
  )
}
