import { Info, Scale } from 'lucide-react'
import type { ComparisonResult } from '@/types/api'

export function TradeoffNotes({ result }: { result: ComparisonResult }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <h3 className="mb-2 flex items-center gap-2 font-display text-sm font-semibold text-muted">
          <Scale className="size-4" aria-hidden /> Trade-offs
        </h3>
        <ul className="space-y-2 text-sm leading-relaxed text-ink">
          {result.tradeoffs.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="mb-2 flex items-center gap-2 font-display text-sm font-semibold text-muted">
          <Info className="size-4" aria-hidden /> Comparability
        </h3>
        {result.comparability_notes.length ? (
          <ul className="space-y-2 text-sm leading-relaxed text-muted">
            {result.comparability_notes.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">Same data source, quality, duration and sampling. Values compare directly.</p>
        )}
      </div>
    </div>
  )
}
