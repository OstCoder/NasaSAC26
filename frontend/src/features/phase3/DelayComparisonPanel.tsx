import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { useApiResource } from '@/hooks/useApiResource'
import { useApp } from '@/hooks/useAppContext'
import { usePhase3Windows } from '@/hooks/useScenario'
import { api } from '@/services/api'
import { cn } from '@/lib/utils'
import type { Phase3WindowSummary, RescheduleResult, Site } from '@/types/api'

const pct = (value: number | null | undefined) => (value == null ? '—' : `${Math.round(value)}%`)

/** Signed percentage-point change, phrased as an operational fact, never a recommendation. */
function Delta({ before, after, good }: { before: number | null; after: number | null; good: boolean }) {
  if (before == null || after == null) return <span className="text-faint">—</span>
  const delta = Math.round((after - before) * 10) / 10
  const word = delta === 0 ? 'unchanged' : delta > 0 ? 'more' : 'less'
  return (
    <span
      className={cn('num text-xs', delta === 0 ? 'text-faint' : good ? (delta > 0 ? 'text-both' : 'text-sun') : (delta > 0 ? 'text-sun' : 'text-both'))}
      title={`${pct(before)} → ${pct(after)} of the 168 h window`}
    >
      {pct(before)} → {pct(after)} ({delta > 0 ? '+' : ''}{delta} pts {word})
    </span>
  )
}

function CommittedRow({ site, windows }: { site: Site; windows?: Record<string, Phase3WindowSummary> }) {
  const initial = windows?.initial
  const alternative = windows?.alternative
  const ready = (w?: Phase3WindowSummary) => w?.available && w.summary
  if (!ready(initial) && !ready(alternative)) {
    return (
      <tr>
        <td className="border-t border-rule-soft px-2 py-1.5 text-ink">{site.name}</td>
        <td colSpan={3} className="border-t border-rule-soft px-2 py-1.5 text-xs text-faint">
          committed windows not available for this site
        </td>
      </tr>
    )
  }
  const s = ready(initial) ? initial!.summary : null
  const a = ready(alternative) ? alternative!.summary : null
  return (
    <tr>
      <td className="border-t border-rule-soft px-2 py-1.5 text-ink">{site.name}</td>
      <td className="border-t border-rule-soft px-2 py-1.5"><Delta before={s?.sun_visible_pct ?? null} after={a?.sun_visible_pct ?? null} good /></td>
      <td className="border-t border-rule-soft px-2 py-1.5"><Delta before={s?.earth_visible_pct ?? null} after={a?.earth_visible_pct ?? null} good /></td>
      <td className="border-t border-rule-soft px-2 py-1.5"><Delta before={s?.both_visible_pct ?? null} after={a?.both_visible_pct ?? null} good /></td>
    </tr>
  )
}

const fmtUnit = (unit: string, value: number | null) =>
  value == null ? '—' : unit === '%' ? `${Math.round(value)}%` : `${Math.round(value * 10) / 10} ${unit}`

/**
 * Phase 4 Task 4: what a ten-day landing delay does to the mission.
 * Two layers, never merged: (1) the committed before/after for every
 * candidate (offline, from the stored 1–8 Dec vs 11–18 Dec series), and
 * (2) an interactive reschedule of the selected site that recomputes with
 * the same engine the planner uses. Metric changes are stated, sites are
 * not ranked.
 */
export function DelayComparisonPanel() {
  const { config, sites, mode } = useApp()
  const windows = usePhase3Windows()
  const bySite = new Map((windows.data?.sites ?? []).map((s) => [s.site_id, s.windows]))

  const presets = config.simulation?.landing_presets ?? []
  const initial = presets.find((p) => p.key === 'initial') ?? presets[0]
  const alternative = presets.find((p) => p.key === 'alternative') ?? presets[1]
  const duration = config.simulation?.default_duration_hours ?? 168

  const [siteId, setSiteId] = React.useState(sites[0]?.id ?? '')
  const [requested, setRequested] = React.useState(false)
  const key = requested && siteId && initial && alternative
    ? `reschedule:${siteId}:${initial.utc}:${alternative.utc}:${duration}:${mode}`
    : null
  const reschedule = useApiResource<RescheduleResult>(key, () =>
    api.reschedule({
      location: { site_id: siteId },
      original_landing_utc: initial!.utc,
      proposed_landing_utc: alternative!.utc,
      duration_hours: duration,
      mode,
    }))

  const liveError = reschedule.error
  const offlineHint = liveError && (liveError.status === 503 || liveError.code.includes('UNAVAILABLE'))

  return (
    <Card>
      <CardHeader
        title="Landing-delay comparison"
        description={
          initial && alternative
            ? `Before/after: ${initial.label} (${initial.utc.slice(0, 10)}) vs ${alternative.label} (${alternative.utc.slice(0, 10)}), each exactly 168 h.`
            : 'Loading the mission window presets…'
        }
      />
      <CardContent>
        {windows.error && <ErrorNotice error={windows.error} />}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-faint">
                <th className="px-2 py-1.5 font-medium">Candidate</th>
                <th className="px-2 py-1.5 font-medium" title="Share of the window with the Sun above the skyline">Sun-visible share</th>
                <th className="px-2 py-1.5 font-medium" title="Share of the window with Earth above the skyline">Earth-visible share</th>
                <th className="px-2 py-1.5 font-medium" title="Share of the window with both above the skyline">Simultaneous share</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <CommittedRow key={site.id} site={site} windows={bySite.get(site.id)} />
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-faint">
          Committed data, offline: percentages of the 168 h window from the stored
          Horizons series and LOLA skylines. The change is a property of the dates,
          not a site ranking.
        </p>

        <div className="mt-4 rounded-lg border border-rule-soft p-3">
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs text-muted" htmlFor="delay-site">
              Recompute for
            </label>
            <select
              id="delay-site"
              className="rounded border border-rule-soft bg-panel px-2 py-1 text-xs text-ink"
              value={siteId}
              onChange={(e) => { setSiteId(e.target.value); setRequested(false) }}
            >
              {sites.map((site) => (
                <option key={site.id} value={site.id}>{site.name}</option>
              ))}
            </select>
            <Button size="sm" variant="outline" onClick={() => setRequested(true)} disabled={!siteId}>
              Compare dates
            </Button>
          </div>
          {liveError && (
            <div className="mt-2">
              <ErrorNotice error={liveError} />
              {offlineHint && (
                <p className="mt-1 text-xs text-faint">
                  The live recompute needs the ephemeris provider; switch the app to
                  Demo Mode or try again when the provider is reachable.
                </p>
              )}
            </div>
          )}
          {reschedule.data && (
            <div className="mt-3" role="region" aria-live="polite" aria-label="Reschedule comparison result">
              <p className="text-xs text-muted">
                Shift: <span className="num text-ink">{reschedule.data.shift_hours} h</span>
                {' '}— {reschedule.data.comparison.comparable ? 'same site and duration, directly comparable.' : 'not directly comparable (see notes).'}
              </p>
              <table className="mt-2 w-full text-left text-xs">
                <thead>
                  <tr className="text-faint">
                    <th className="px-2 py-1 font-medium">Metric</th>
                    <th className="px-2 py-1 font-medium">{initial?.label ?? 'Original'}</th>
                    <th className="px-2 py-1 font-medium">{alternative?.label ?? 'Proposed'}</th>
                    <th className="px-2 py-1 font-medium">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {reschedule.data.headline_changes.map((d) => (
                    <tr key={d.id}>
                      <td className="border-t border-rule-soft px-2 py-1 text-ink" title={d.statement}>{d.label}</td>
                      <td className="num border-t border-rule-soft px-2 py-1">{fmtUnit(d.unit, d.a)}</td>
                      <td className="num border-t border-rule-soft px-2 py-1">{fmtUnit(d.unit, d.b)}</td>
                      <td className="num border-t border-rule-soft px-2 py-1">
                        {d.delta == null ? '—' : `${d.delta > 0 ? '+' : ''}${Math.round(d.delta * 10) / 10} ${d.unit}`}
                        {d.either_censored && <span className="ml-1 text-faint">(window-limited)</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <ul className="mt-2 space-y-1 text-xs text-faint">
                {reschedule.data.comparison.tradeoffs.slice(0, 3).map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          )}
          {!reschedule.data && !reschedule.error && requested && (
            <p className="mt-3 text-xs text-faint">Recomputing both dates…</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
