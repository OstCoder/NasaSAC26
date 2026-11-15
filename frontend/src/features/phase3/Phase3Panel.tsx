import { ErrorNotice } from '@/components/ErrorNotice'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { usePhase3Windows, useReadiness } from '@/hooks/useScenario'
import { cn } from '@/lib/utils'
import type { Phase3WindowSummary, SiteReadiness } from '@/types/api'

const WINDOWS = [
  { key: 'initial', label: '1–8 Dec 2026' },
  { key: 'alternative', label: '11–18 Dec 2026' },
] as const

const pct = (value: number | null | undefined) => (value == null ? '—' : `${Math.round(value)}%`)
const km = (metres: number) => `${(metres / 1000).toFixed(metres >= 10_000 ? 0 : 1)} km`

function WindowRow({ label, row }: { label: string; row?: Phase3WindowSummary }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-t border-rule-soft pt-1.5 text-xs">
      <span className="text-muted">{label}</span>
      {row?.available && row.summary ? (
        <span className="num text-ink" title="Terrain-adjusted geometry: body centre above the LOLA skyline">
          {pct(row.summary.sun_visible_pct)} Sun · {pct(row.summary.earth_visible_pct)} Earth ·{' '}
          {pct(row.summary.both_visible_pct)} both
        </span>
      ) : (
        <span className="text-faint">not available</span>
      )}
    </div>
  )
}

function SiteCard({
  site,
  windows,
}: {
  site: SiteReadiness
  windows: Record<string, Phase3WindowSummary>
}) {
  const mask = site.mask
  const near = mask?.tiers?.near
  const far = mask?.tiers?.far
  return (
    <div className="rounded-lg border border-rule-soft p-3">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="font-display text-sm font-semibold text-ink">{site.name ?? site.site_id}</h3>
        <span className={cn('text-xs font-medium', site.ready ? 'text-both' : 'text-sun')}>
          {site.ready ? 'Ready' : 'Not ready'}
        </span>
      </div>
      <p className="mt-1 text-xs text-faint">
        {near && far
          ? `Skyline ${near.pixel_m} m to ${km(near.max_range_m)}, then ${far.pixel_m} m to ${km(far.max_range_m)}`
          : mask
            ? `Skyline to ${km(mask.max_range_km * 1000)}`
            : 'No LOLA skyline'}
        {mask ? ` · max ${mask.max_obstruction_deg.toFixed(2)}°` : ''}
      </p>
      {WINDOWS.map(({ key, label }) => (
        <WindowRow key={key} label={label} row={windows[key]} />
      ))}
      {!site.ready && site.problems.length > 0 && (
        <p className="mt-2 text-xs text-sun">{site.problems[0]}</p>
      )}
    </div>
  )
}

/**
 * Phase 3 hand-off in the UI: whether each candidate has the data a visibility
 * calculation needs, how wide its skyline is, and the terrain-adjusted Sun/Earth
 * share of both mission windows. Geometry only - not power and not a link budget.
 */
export function Phase3Panel() {
  const readiness = useReadiness()
  const windows = usePhase3Windows()
  const error = readiness.error ?? windows.error
  const bySite = new Map((windows.data?.sites ?? []).map((s) => [s.site_id, s.windows]))

  return (
    <Card>
      <CardHeader
        title="Data readiness"
        description="Computed offline from the committed hourly Sun/Earth series and two-tier LOLA skyline (5 m pixels near the site, 80 m out to 150 km). Percentages are geometry: Sun above terrain is not power, Earth above terrain is not a link budget."
      />
      <CardContent className="space-y-4">
        {error && <ErrorNotice error={error} />}
        {!readiness.data || !windows.data ? (
          !error && <p className="text-sm text-muted">Loading data readiness…</p>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              {readiness.data.sites.map((site) => (
                <SiteCard key={site.site_id} site={site} windows={bySite.get(site.site_id) ?? {}} />
              ))}
            </div>
            <p className="text-xs text-faint">
              Ready means both mission windows are stored and a LOLA skyline exists. The skyline
              reaches 150 km, past the distance where lunar curvature puts even the highest terrain
              below the horizon, so no obstruction-capable ground is unsampled.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
