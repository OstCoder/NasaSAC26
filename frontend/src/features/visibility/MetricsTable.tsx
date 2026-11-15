import { Tooltip } from '@/components/ui/tooltip'
import { fmtMetric } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { MetricCategory, MetricValue } from '@/types/api'

const GROUPS: { id: MetricCategory; label: string; dot: string; tone: string }[] = [
  { id: 'sun', label: 'Sunlight', dot: 'bg-sun', tone: 'text-sun' },
  { id: 'earth', label: 'Earth line of sight', dot: 'bg-earth', tone: 'text-earth' },
  { id: 'combined', label: 'Combined', dot: 'bg-both', tone: 'text-both' },
  { id: 'geometry', label: 'Geometry', dot: 'bg-faint', tone: 'text-faint' },
]

/** Mission summary. Values limited by the window length are shown as lower bounds (≥). */
export function MetricsTable({ metrics }: { metrics: MetricValue[] }) {
  return (
    <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2 xl:grid-cols-4">
      {GROUPS.map((g) => {
        const rows = metrics.filter((m) => m.category === g.id)
        if (!rows.length) return null
        return (
          <div key={g.id}>
            <h3 className="mb-1 flex items-center gap-2 font-display text-sm font-semibold text-muted">
              <span className={cn('size-2 rounded-full', g.dot)} aria-hidden />
              {g.label}
            </h3>
            <dl>
              {rows.map((m) => (
                <div key={m.id} className="flex items-baseline justify-between gap-3 border-t border-rule-soft py-1.5">
                  <Tooltip content={m.description}>
                    <dt className="cursor-help text-[12px] text-muted">
                      {m.label}
                      {m.unit === '%' ? ' (share)' : ''}
                    </dt>
                  </Tooltip>
                  <dd className={cn('num text-base text-ink', g.tone)}>
                    {m.censored && (
                      <Tooltip content="Touches the edge of the analysis window, so the true value may be larger.">
                        <span className="mr-0.5 cursor-help text-faint">≥</span>
                      </Tooltip>
                    )}
                    {fmtMetric(m.value, m.unit)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )
      })}
    </div>
  )
}
