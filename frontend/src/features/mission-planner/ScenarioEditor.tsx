import * as React from 'react'
import { Field, Input, Select } from '@/components/ui/field'
import { DURATION_PRESETS_HOURS } from '@/config/app'
import { siteDraftLocation, useApp, type ScenarioDraft } from '@/hooks/useAppContext'
import { fmtHours, fmtUtc, inputToIso, isoToInput } from '@/lib/format'
import { cn } from '@/lib/utils'

const CUSTOM = '__custom__'

export function rangeProblem(draft: ScenarioDraft, start: string, end: string): string | null {
  const t = Date.parse(draft.landing_utc)
  if (Number.isNaN(t)) return 'Enter a valid UTC landing time.'
  const tEnd = t + draft.duration_hours * 3_600_000
  if (t < Date.parse(start) || tEnd > Date.parse(end))
    return `The mission window must stay between ${fmtUtc(start)} and ${fmtUtc(end)} UTC.`
  return null
}

/**
 * Edits one ScenarioDraft (site or coordinates, landing time, duration).
 * Shared by the planner, the comparison view and the rescheduler.
 */
export function ScenarioEditor({
  draft,
  onChange,
  showSite = true,
  showDate = true,
  showDuration = true,
  dense = false,
}: {
  draft: ScenarioDraft
  onChange: (d: ScenarioDraft) => void
  showSite?: boolean
  showDate?: boolean
  showDuration?: boolean
  dense?: boolean
}) {
  const { sites, config, features } = useApp()
  const sim = config.simulation
  const isCustom = !draft.location.site_id
  const selectedSite = !isCustom ? sites.find((s) => s.id === draft.location.site_id) : undefined
  const [lat, setLat] = React.useState(String(draft.location.latitude_deg ?? -87.0))
  const [lon, setLon] = React.useState(String(draft.location.longitude_deg ?? 0))

  React.useEffect(() => {
    if (isCustom) {
      setLat(String(draft.location.latitude_deg ?? ''))
      setLon(String(draft.location.longitude_deg ?? ''))
    }
  }, [isCustom, draft.location.latitude_deg, draft.location.longitude_deg])

  const latNum = Number(lat)
  const lonNum = Number(lon)
  const coordError =
    lat === '' || Number.isNaN(latNum) || latNum < -90 || latNum > 90
      ? 'Latitude must be between −90 and 90.'
      : Math.abs(latNum) >= 89.999999
        ? 'Exactly at the pole, azimuth is undefined. Use e.g. −89.999.'
        : lon === '' || Number.isNaN(lonNum) || lonNum < -180 || lonNum > 180
          ? 'Longitude must be between −180 and 180 (east positive).'
          : null

  const applyCoords = () => {
    if (coordError) return
    onChange({
      ...draft,
      location: { latitude_deg: latNum, longitude_deg: lonNum },
      locationName: `Custom ${Math.abs(latNum).toFixed(3)}°${latNum < 0 ? 'S' : 'N'} ${Math.abs(lonNum).toFixed(3)}°${lonNum < 0 ? 'W' : 'E'}`,
    })
  }

  const candidateIds = config.mission.candidate_sites
  const candidateList = candidateIds.flatMap((id) => sites.filter((s) => s.id === id))
  const otherSites = sites.filter((s) => !candidateIds.includes(s.id))

  const problem = rangeProblem(draft, sim.supported_start_utc, sim.supported_end_utc)

  return (
    <div className={cn('grid gap-3', dense ? 'grid-cols-1' : 'sm:grid-cols-2')}>
      {showSite && <Field label="Landing site" className={dense ? '' : 'sm:col-span-2'}>
        <Select
          value={isCustom ? CUSTOM : (draft.location.site_id ?? '')}
          onChange={(e) => {
            if (e.target.value === CUSTOM) {
              setLat(String(draft.location.latitude_deg ?? -87))
              onChange({ ...draft, location: { latitude_deg: -87.0, longitude_deg: 0.0 }, locationName: 'Custom −87.000° 0.000°' })
              return
            }
            const site = sites.find((s) => s.id === e.target.value)
            if (site) onChange({ ...draft, ...siteDraftLocation(site) })
          }}
        >
          {candidateList.length > 0 && (
            <optgroup label="Mission candidates">
              {candidateList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </optgroup>
          )}
          {otherSites.length > 0 && (
            <optgroup label="Other sites">
              {otherSites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </optgroup>
          )}
          {features.custom_coordinates && <option value={CUSTOM}>Custom coordinates…</option>}
        </Select>
        {selectedSite?.elevation_m != null && (
          <p className="text-xs text-muted">
            LOLA elevation {Math.round(selectedSite.elevation_m)} m
            {selectedSite.slope_deg != null && <> · slope {selectedSite.slope_deg.toFixed(1)}°</>}
            {selectedSite.nearest_psr &&
              <> · nearest mapped PSR {selectedSite.nearest_psr.distance_km.toFixed(1)} km ({selectedSite.nearest_psr.label})</>}
          </p>
        )}
      </Field>}

      {showSite && isCustom && (
        <div className={cn('grid grid-cols-[1fr_1fr_auto] items-end gap-2', dense ? '' : 'sm:col-span-2')}>
          <Field label="Latitude (°)">
            <Input inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} onBlur={applyCoords}
              onKeyDown={(e) => e.key === 'Enter' && applyCoords()} aria-invalid={Boolean(coordError)} />
          </Field>
          <Field label="Longitude (°E)">
            <Input inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} onBlur={applyCoords}
              onKeyDown={(e) => e.key === 'Enter' && applyCoords()} aria-invalid={Boolean(coordError)} />
          </Field>
          <button onClick={applyCoords} disabled={Boolean(coordError)}
            className="h-9 rounded-md border border-rule px-3 text-sm text-ink hover:bg-raised disabled:opacity-40">
            Set
          </button>
          {coordError ? (
            <p className="col-span-3 text-xs text-alert">{coordError}</p>
          ) : (
            <p className="col-span-3 text-xs text-faint">
              Or click the map. Custom points have no LOLA skyline, so results use the flat geometric
              horizon and are labelled geometric only.
            </p>
          )}
        </div>
      )}

      {showDate && (
        <Field label="Landing time (UTC)">
          <Input
            type="datetime-local"
            value={isoToInput(draft.landing_utc)}
            min={isoToInput(sim.supported_start_utc)}
            max={isoToInput(sim.supported_end_utc)}
            onChange={(e) => e.target.value && onChange({ ...draft, landing_utc: inputToIso(e.target.value) })}
          />
        </Field>
      )}

      {showDate && (sim.landing_presets ?? []).length > 0 && (
        <div className={cn('flex flex-wrap items-center gap-1.5 self-end', dense ? '' : 'sm:col-span-2')}>
          <span className="text-[13px] text-muted">Mission dates</span>
          {(sim.landing_presets ?? []).map((p) => (
            <button
              key={p.key}
              onClick={() => onChange({ ...draft, landing_utc: p.utc })}
              className={cn(
                'h-9 whitespace-nowrap rounded-md px-1.5 text-xs transition-colors',
                draft.landing_utc === p.utc ? 'bg-raised text-ink' : 'text-muted hover:text-ink',
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      {showDuration && (
        <Field label="Mission duration" hint={fmtHours(draft.duration_hours)}>
          <div className="flex flex-wrap items-center gap-1.5">
            <Input
              type="number"
              min={sim.min_duration_hours}
              max={sim.max_duration_hours}
              value={draft.duration_hours}
              onChange={(e) => {
                const v = Number(e.target.value)
                // Clamp to the configured range here so the input cannot produce a
                // request the backend is certain to reject.
                if (v > 0)
                  onChange({
                    ...draft,
                    duration_hours: Math.min(Math.max(v, sim.min_duration_hours), sim.max_duration_hours),
                  })
              }}
              className="w-24"
              aria-label="Duration in hours"
            />
            <div className="flex gap-0.5">
              {DURATION_PRESETS_HOURS.map((h) => (
                <button
                  key={h}
                  onClick={() => onChange({ ...draft, duration_hours: h })}
                  className={cn(
                    'h-9 whitespace-nowrap rounded-md px-1.5 text-xs transition-colors',
                    draft.duration_hours === h ? 'bg-raised text-ink' : 'text-muted hover:text-ink',
                  )}
                >
                  {h < 48 ? `${h} h` : h === 708 ? '29.5 d' : `${h / 24} d`}
                </button>
              ))}
            </div>
          </div>
        </Field>
      )}

      {problem && <p className={cn('text-xs text-alert', dense ? '' : 'sm:col-span-2')}>{problem}</p>}
    </div>
  )
}
