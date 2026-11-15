import { RefreshCw, Satellite } from 'lucide-react'
import * as React from 'react'
import { Tooltip } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type { JplStatus as Status } from '@/types/api'

/** Live reachability of JPL Horizons and Moon Trek, as seen from the LunaNav server. */
export function JplStatusPill() {
  const [status, setStatus] = React.useState<Status | null>(null)
  const [checking, setChecking] = React.useState(false)

  const check = React.useCallback((force: boolean) => {
    setChecking(true)
    api.jplStatus(force)
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setChecking(false))
  }, [])
  React.useEffect(() => check(false), [check])
  React.useEffect(() => {
    const id = window.setInterval(() => check(true), 5 * 60 * 1000)
    return () => window.clearInterval(id)
  }, [check])

  const up = status ? [status.horizons.reachable, status.trek.reachable].filter(Boolean).length : 0
  const tone = checking && !status ? 'checking' : !status ? 'down' : up === 2 ? 'up' : up === 1 ? 'partial' : 'down'
  const label = { checking: 'Checking JPL…', up: 'JPL connected', partial: 'JPL partly reachable', down: 'JPL offline' }[tone]

  return (
    <Tooltip
      content={
        status ? (
          <div className="space-y-1.5">
            {[status.horizons, status.trek].map((s) => (
              <p key={s.service}>
                <span className={s.reachable ? 'text-both' : 'text-alert'}>{s.reachable ? 'Reachable' : 'Not reachable'}</span>
                {': '}{s.service}{s.reachable ? ` (${s.latency_ms} ms)` : ''}
                {!s.reachable && <span className="block text-muted">{s.message}</span>}
              </p>
            ))}
            {status.horizons_cache && status.horizons_cache.months.length > 0 && (
              <p className="text-muted">Cached Horizons months: {status.horizons_cache.months.join(', ')}</p>
            )}
            <p className="text-faint">Click to check again.</p>
          </div>
        ) : 'Could not ask the LunaNav server for JPL status.'
      }
    >
      <button
        onClick={() => check(true)}
        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-rule-soft px-2.5 text-[13px] text-muted hover:text-ink"
      >
        {checking ? <RefreshCw className="size-3.5 animate-spin" aria-hidden /> : <Satellite className="size-3.5" aria-hidden />}
        <span
          aria-hidden
          className={cn('size-2 rounded-full',
            tone === 'up' && 'bg-both', tone === 'partial' && 'bg-sun', tone === 'down' && 'bg-alert', tone === 'checking' && 'bg-faint')}
        />
        {label}
      </button>
    </Tooltip>
  )
}
