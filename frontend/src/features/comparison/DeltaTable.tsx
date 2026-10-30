import { Tooltip } from '@/components/ui/tooltip'
import { fmtMetric, fmtSigned } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { MetricDelta } from '@/types/api'

const EPS: Record<string, number> = { h: 0.25, '%': 0.5, deg: 0.05 }

/**
 * Side-by-side metric table. Change cells are tinted by *availability*
 * (mint: B has more of the body; coral: less, or a longer outage), never by
 * "better/worse site": that judgement needs constraints this app doesn't model.
 */
export function DeltaTable({ deltas, aLabel = 'A', bLabel = 'B' }: { deltas: MetricDelta[]; aLabel?: string; bLabel?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-sm">
        <thead>
          <tr className="border-b border-rule text-left text-[13px] text-muted">
            <th className="py-2 pr-3 font-medium">Measure</th>
            <th className="num px-3 py-2 text-right font-medium">{aLabel}</th>
            <th className="num px-3 py-2 text-right font-medium">{bLabel}</th>
            <th className="py-2 pl-3 text-right font-medium">Change ({bLabel} vs {aLabel})</th>
          </tr>
        </thead>
        <tbody>
          {deltas.map((d) => {
            const small = d.delta === null || Math.abs(d.delta) < (EPS[d.unit] ?? 1e-6)
            const signed = (d.delta ?? 0) * d.availability_direction
            return (
              <tr key={d.id} className="border-b border-rule-soft last:border-0">
                <td className="py-2 pr-3">
                  <Tooltip content={d.statement}>
                    <span className="cursor-help text-ink">
                      {d.label}
                      {d.unit === '%' && <span className="text-muted"> (share)</span>}
                    </span>
                  </Tooltip>
                </td>
                <td className="num px-3 py-2 text-right text-muted">{fmtMetric(d.a, d.unit)}</td>
                <td className="num px-3 py-2 text-right text-muted">{fmtMetric(d.b, d.unit)}</td>
                <td className="py-2 pl-3 text-right">
                  <span
                    className={cn(
                      'num inline-block min-w-[84px] rounded px-2 py-0.5 text-right font-medium',
                      small && 'text-faint',
                      !small && d.availability_direction === 0 && 'bg-raised text-ink',
                      !small && signed > 0 && 'bg-both/15 text-both',
                      !small && signed < 0 && 'bg-alert/15 text-alert',
                    )}
                  >
                    {small ? 'no change' : fmtSigned(d.delta, d.unit)}
                    {d.either_censored && !small && <span title="At least one value is a lower bound"> *</span>}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
