import { AlertTriangle, CalendarX, DatabaseZap, PlugZap, SatelliteDish } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { fmtUtc } from '@/lib/format'
import type { ApiError } from '@/services/api'

/** Turns API errors into direction: what happened and what to do next. */
export function ErrorNotice({ error, onUseDemo }: { error: ApiError; onUseDemo?: () => void }) {
  let Icon = AlertTriangle
  let title = 'The calculation could not run'
  let action: React.ReactNode = null
  const d = error.details as { supported_start_utc?: string; supported_end_utc?: string }

  if (error.code === 'OUT_OF_SUPPORTED_RANGE') {
    Icon = CalendarX
    title = 'Dates outside the supported window'
    if (d.supported_start_utc && d.supported_end_utc)
      action = (
        <p className="text-muted">
          Choose a landing time and duration that stay between {fmtUtc(d.supported_start_utc)} and{' '}
          {fmtUtc(d.supported_end_utc)} UTC.
        </p>
      )
  } else if (error.code === 'SCIENTIFIC_DATA_UNAVAILABLE') {
    Icon = DatabaseZap
    title = 'Scientific data is not loaded'
    action = (
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-muted">
          No values are shown rather than substituting demo data. Add Horizons tables and LOLA horizon masks
          (see docs/ADAPTATION_GUIDE.md), or switch to demo mode.
        </p>
        {onUseDemo && (
          <Button size="sm" onClick={onUseDemo}>
            Switch to demo mode
          </Button>
        )}
      </div>
    )
  } else if (error.code === 'JPL_UNAVAILABLE') {
    Icon = SatelliteDish
    title = 'NASA/JPL data could not be used'
    action = (
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-muted">
          The LunaNav server needs internet access to JPL. Run <code className="text-ink">python scripts/check_jpl.py</code> in
          the backend folder for a diagnosis, or switch to demo mode.
        </p>
        {onUseDemo && <Button size="sm" onClick={onUseDemo}>Switch to demo mode</Button>}
      </div>
    )
  } else if (error.code === 'BACKEND_UNREACHABLE') {
    Icon = PlugZap
    title = 'Backend not reachable'
  } else if (error.code === 'INVALID_INPUT') {
    title = 'Check the inputs'
  }

  return (
    <div role="alert" className="flex gap-3 rounded-md border border-alert/40 bg-alert/5 p-3 text-sm">
      <Icon className="mt-0.5 size-5 shrink-0 text-alert" aria-hidden />
      <div className="space-y-1">
        <p className="font-medium text-ink">{title}</p>
        <p className="text-muted">{error.message}</p>
        {action}
      </div>
    </div>
  )
}
