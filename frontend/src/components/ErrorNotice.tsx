import { AlertTriangle, CalendarX, DatabaseZap, PlugZap, RotateCw, SatelliteDish } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { fmtUtc } from '@/lib/format'
import type { ApiError } from '@/services/api'

/** Turns API errors into direction: what happened and what to do next. */
export function ErrorNotice({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
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
    title = 'That terrain data is not available'
    action = (
      <p className="text-muted">
        No values are invented to fill the gap. Pick a site with a committed terrain profile, or use a
        flat-horizon result that is clearly labelled.
      </p>
    )
  } else if (error.code === 'JPL_UNAVAILABLE') {
    Icon = SatelliteDish
    title = 'NASA/JPL data could not be used'
    action = (
      <p className="text-muted">
        The LunaNav server needs internet access to JPL. Run{' '}
        <code className="text-ink">python scripts/check_jpl.py</code> in the backend folder for a
        diagnosis, then try again.
      </p>
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
        {onRetry && (
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RotateCw /> Try again
          </Button>
        )}
      </div>
    </div>
  )
}
