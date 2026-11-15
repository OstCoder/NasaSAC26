import { ExternalLink, ShieldAlert } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { LunarMap, type MapSelection } from '@/features/lunar-map'
import { useApp } from '@/hooks/useAppContext'
import { useScienceSiteContext } from '@/hooks/useScenario'
import { fmtLat, fmtLon, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { ScienceSiteContext, Site } from '@/types/api'

function km(value: number): string {
  if (value === 0) return '0 km (inside)'
  return `${value.toFixed(value < 10 ? 2 : 1)} km`
}

function Pct({ value }: { value: number | null | undefined }) {
  return <span className="num">{value == null ? '—' : `${value.toFixed(0)}%`}</span>
}

function CandidateRow({ site, selected, onSelect }: {
  site: Site
  selected: boolean
  onSelect: () => void
}) {
  const context = useScienceSiteContext(site.id)
  const nearest = context.data?.nearest_psr
  const initial = context.data?.visibility_windows.initial
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        'grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 border-t border-rule-soft px-1 py-2 text-left first:border-t-0',
        selected ? 'bg-signal/5' : 'hover:bg-raised/60',
      )}
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-ink">{site.name}</span>
        <span className="text-xs text-faint">
          {nearest ? `${nearest.label} · ${km(nearest.boundary_distance_km)}` : 'PSR: loading or unavailable'}
        </span>
      </span>
      <span className="text-right text-xs text-muted">
        {initial?.available ? (
          <>
            <span className="block">Sun <Pct value={initial.sun_visible_pct} /> · Earth <Pct value={initial.earth_visible_pct} /></span>
            <span className="block text-faint">1–8 Dec window</span>
          </>
        ) : (
          <span className="block text-faint">window unavailable</span>
        )}
      </span>
    </button>
  )
}

function ContextCard({ siteId }: { siteId: string }) {
  const context = useScienceSiteContext(siteId)
  if (context.error) return <ErrorNotice error={context.error} onRetry={context.retry} />
  if (!context.data) return <p role="status" className="text-sm text-muted">Loading the science context…</p>
  return <ContextBody context={context.data} />
}

function ContextBody({ context }: { context: ScienceSiteContext }) {
  const { site, nearest_psr: psr, terrain, science } = context
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-md border border-rule-soft p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-faint">Nearest mapped PSR</p>
          <p className="mt-1 text-sm font-medium text-ink">{psr.label}</p>
          <dl className="mt-2 space-y-1 text-xs">
            <div className="flex justify-between gap-3"><dt className="text-muted">Boundary distance</dt><dd className="num text-ink">{km(psr.boundary_distance_km)}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Centroid distance</dt><dd className="num text-ink">{km(psr.centroid_distance_km)}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Mapped area</dt><dd className="num text-ink">{psr.area_km2.toFixed(1)} km²</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Positional uncertainty</dt><dd className="num text-ink">±{psr.distance_uncertainty_km * 1000} m</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Within 10 km</dt><dd className="num text-ink">{context.nearby_count}</dd></div>
          </dl>
          <p className="mt-2 text-[11px] leading-relaxed text-faint">
            Boundary distance is the minimum point-to-polygon distance. It is not a rover route,
            slope, thermal path, or proof of accessible ice.
          </p>
        </div>

        <div className="rounded-md border border-rule-soft p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-faint">Terrain basis</p>
          <p className="mt-1 text-sm font-medium text-ink">
            {terrain.available ? 'Terrain-aware LOLA skyline' : 'Geometric only — no committed mask'}
          </p>
          <dl className="mt-2 space-y-1 text-xs">
            <div className="flex justify-between gap-3"><dt className="text-muted">Near / far pixels</dt><dd className="num text-ink">{terrain.coverage.near.pixel_m ?? '—'} m / {terrain.coverage.far.pixel_m ?? '—'} m</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Sampled range</dt><dd className="num text-ink">{terrain.coverage.max_sampled_range_km ?? '—'} km</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Observer height</dt><dd className="num text-ink">{terrain.observer_height_m} m</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-muted">Elevation / slope</dt><dd className="num text-ink">{site.elevation_m == null ? '—' : `${Math.round(site.elevation_m)} m`} / {site.slope_deg == null ? '—' : `${site.slope_deg.toFixed(1)}°`}</dd></div>
          </dl>
          <p className="mt-2 text-[11px] leading-relaxed text-faint">{terrain.source}</p>
        </div>
      </div>

      <div className="rounded-md border border-sun/30 bg-sun/5 p-3">
        <p className="flex items-center gap-2 text-sm font-medium text-ink">
          <ShieldAlert className="size-4 text-sun" aria-hidden />
          Water ice: not assessed
        </p>
        <p className="mt-1 max-w-[90ch] text-xs leading-relaxed text-muted">
          {science.psr_interpretation} No detection, concentration, depth, temperature, or resource
          estimate is available in the committed data. Unknown is not evidence of absence.
        </p>
      </div>

      <div>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-faint">Committed mission windows</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {Object.entries(context.visibility_windows).map(([key, window]) => (
            <div key={key} className="rounded border border-rule-soft p-2 text-xs">
              <p className="font-medium text-ink">{window.label ?? key}</p>
              {window.available ? (
                <>
                  <p className="num mt-1 text-muted">
                    Sun <Pct value={window.sun_visible_pct} /> · Earth <Pct value={window.earth_visible_pct} />
                  </p>
                  <p className="num text-faint">
                    Longest darkness {window.longest_sun_blackout_hours == null ? '—' : `${window.longest_sun_blackout_hours.toFixed(1)} h`}
                    {' · '}Earth blackout {window.longest_earth_blackout_hours == null ? '—' : `${window.longest_earth_blackout_hours.toFixed(1)} h`}
                  </p>
                  {(window.start_utc || window.stop_utc) && (
                    <p className="num mt-1 text-faint">
                      {window.start_utc ? fmtUtc(window.start_utc) : '—'} to {window.stop_utc ? fmtUtc(window.stop_utc) : '—'} UTC
                    </p>
                  )}
                </>
              ) : (
                <p className="mt-1 text-faint">{window.reason ?? 'No committed calculation.'}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {context.nearby_psrs.length > 1 && (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-faint">Other mapped PSRs within 10 km</p>
          <ul className="space-y-1 text-xs text-muted">
            {context.nearby_psrs.slice(1).map((other) => (
              <li key={other.psr_id} className="flex justify-between gap-3 border-t border-rule-soft pt-1 first:border-t-0 first:pt-0">
                <span className="truncate">{other.label}</span>
                <span className="num shrink-0 text-ink">{km(other.boundary_distance_km)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="rounded-md border border-rule-soft p-3 text-xs text-muted">
        <summary className="cursor-pointer font-medium text-ink">Limits and provenance</summary>
        <ul className="mt-2 list-disc space-y-1 pl-4">
          {context.limits.map((limit) => <li key={limit}>{limit}</li>)}
        </ul>
        <p className="mt-2 text-faint">
          PSR: {context.provenance.psr}. Terrain: {context.provenance.terrain}. Ephemeris: {context.provenance.ephemeris}.
        </p>
      </details>
    </div>
  )
}

const TOPICS: { title: string; body: React.ReactNode }[] = [
  {
    title: 'Why is the lunar south pole important?',
    body: <>The Moon’s spin axis is tilted only about 1.5° from the ecliptic normal, so near the poles the Sun stays close to the horizon. High rims can remain lit for long stretches while adjacent crater floors stay in permanent shadow. That combination makes the region interesting for both solar power and volatile science.</>,
  },
  {
    title: 'What are permanently shadowed regions?',
    body: <>A PSR is ground where direct sunlight does not reach over the long-term solar cycle because of local topography. PSRs are mapped from LOLA-derived shadow masks; the catalogue used here includes polygons larger than 5 km² and does not resolve every small shadow patch.</>,
  },
  {
    title: 'Why does sunlight matter for a spacecraft?',
    body: <>Sunlight is a precondition for solar power, not a promise of it. Panel orientation, shadowing by the lander, dust, temperature and battery behaviour all matter. LunaNav’s power view is a simplified engineering model with documented hypothetical hardware assumptions.</>,
  },
  {
    title: 'How does a lunar lander communicate with Earth?',
    body: <>Direct-to-Earth communication needs the Earth above the local terrain and a link with enough margin. Earth visibility is line of sight, not a working radio link. Antenna pointing, ground-station scheduling, weather and relay options are outside the visibility calculation.</>,
  },
  {
    title: 'Why can a mission delay change conditions?',
    body: <>The Sun and Earth move in the lunar sky, and the terrain blocks different directions at different times. A delay can trade illumination against Earth visibility, blackout length and battery reserve. The rescheduler compares the two committed windows using the same measurement engine.</>,
  },
  {
    title: 'Why are water-ice deposits scientifically important?',
    body: <>Water ice could preserve a record of volatile delivery and could be a resource for future exploration. But a PSR is only a shadow classification. LunaNav does not infer ice from proximity: the science context reports “not assessed” until a verified detection product is added.</>,
  },
]

export function SciencePage() {
  const { sites, config } = useApp()
  const candidateIds = config.mission.candidate_sites
  const candidates = candidateIds.flatMap((id) => sites.filter((site) => site.id === id))
  const fallback = candidates.length > 0 ? candidates : sites
  const [selectedId, setSelectedId] = React.useState(fallback[0]?.id ?? '')
  const [showPsrs, setShowPsrs] = React.useState(true)
  const selected = sites.find((site) => site.id === selectedId)
  const selection: MapSelection | undefined = selected
    ? { lat: selected.latitude_deg, lon: selected.longitude_deg, label: selected.name }
    : undefined
  const context = useScienceSiteContext(selectedId || null)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Science exploration"
          description="Verified PSR geometry and mission context. Proximity is a lead for investigation, not evidence of water ice or a safe traverse."
        />
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-xs text-muted">
                <input type="checkbox" checked={showPsrs} onChange={(event) => setShowPsrs(event.target.checked)} />
                PSR layer
              </label>
              {selected && (
                <p className="num text-xs text-faint">
                  {fmtLat(selected.latitude_deg)}, {fmtLon(selected.longitude_deg)}
                </p>
              )}
            </div>
            <LunarMap
              className="aspect-square w-full"
              sites={sites}
              selections={selection ? { A: selection } : {}}
              activeSlot="A"
              onSelectSite={(site) => setSelectedId(site.id)}
              showPsrs={showPsrs}
              highlightPsrId={context.data?.nearest_psr.psr_id ?? null}
            />
            <p className="text-[11px] leading-relaxed text-faint">
              PSR polygons: NASA/GSFC/Arizona State University LROC, derived from LOLA permanent-shadow
              masks (Mazarico et al. 2011). Gold outline marks the nearest mapped PSR to the selected site.
            </p>
          </div>
          <div className="min-w-0">
            {selected && <ContextCard siteId={selected.id} />}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Candidate comparison" description="The same measured PSR and window context for each mission candidate." />
          <CardContent className="px-2 pb-2">
            {fallback.map((site) => (
              <CandidateRow
                key={site.id}
                site={site}
                selected={site.id === selectedId}
                onSelect={() => setSelectedId(site.id)}
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Scientific model labels" description="Read every number with its basis attached." />
          <CardContent className="space-y-3 text-sm">
            {[
              ['GEOMETRIC MODEL', 'Sun or Earth centre above a flat horizon. No terrain obstruction.'],
              ['TERRAIN-AWARE MODEL', 'Sun or Earth centre above the committed LOLA skyline at its own azimuth.'],
              ['SIMPLIFIED ENERGY MODEL', 'Power and battery estimates with hypothetical spacecraft assumptions, not flight hardware.'],
              ['UNAVAILABLE DATA', 'The requested verified value is missing. LunaNav withholds it rather than filling it with a guess.'],
            ].map(([label, text]) => (
              <div key={label} className="border-t border-rule-soft pt-2 first:border-t-0 first:pt-0">
                <p className="font-display text-xs font-semibold tracking-wide text-ink">{label}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-muted">{text}</p>
              </div>
            ))}
            <p className="text-[11px] leading-relaxed text-faint">
              Coordinate frame: mean Earth / polar axis, east-positive longitude, 1737.4 km reference
              sphere. Distances use the same south-polar stereographic frame as the map. PSR boundary
              products resolve 120 m at 75–82°S and 60 m poleward of 82°S. Time is UTC.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader title="Learn the science" description="Short explanations for the measurements shown across LunaNav." />
        <CardContent className="grid gap-2 md:grid-cols-2">
          {TOPICS.map((topic) => (
            <details key={topic.title} className="rounded-md border border-rule-soft p-3">
              <summary className="cursor-pointer text-sm font-medium text-ink">{topic.title}</summary>
              <p className="mt-2 text-xs leading-relaxed text-muted">{topic.body}</p>
            </details>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader title="Sources and attribution" description="The science view uses only committed, documented products." />
        <CardContent className="grid gap-3 text-xs text-muted sm:grid-cols-2">
          <p>
            <span className="text-ink">PSR boundaries:</span> NASA/GSFC/Arizona State University LROC
            NAC_POLE_PSR_SOUTH companion product, derived from LOLA permanent-shadow masks
            (Mazarico et al. 2011). Regions larger than 5 km² only.
          </p>
          <p>
            <span className="text-ink">Terrain:</span> LOLA south-polar DEMs from the NASA PDS
            Geosciences Node; 5 m/pixel near each site and 80 m/pixel to 150 km. Skyline products are
            committed and reproducible.
          </p>
          <p>
            <span className="text-ink">Ephemeris:</span> NASA JPL Horizons for the live/scientific
            modes; the analytic Meeus model is clearly labelled in Demo Mode.
          </p>
          <p className="flex flex-col gap-1">
            <span className="text-ink">Further reading:</span>
            <a className="inline-flex items-center gap-1 text-signal hover:underline" href="https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH" target="_blank" rel="noreferrer">LROC PSR product <ExternalLink className="size-3" /></a>
            <a className="inline-flex items-center gap-1 text-signal hover:underline" href="https://pgda.gsfc.nasa.gov/products/78" target="_blank" rel="noreferrer">NASA LOLA south-pole topography <ExternalLink className="size-3" /></a>
            <a className="inline-flex items-center gap-1 text-signal hover:underline" href="https://trek.nasa.gov/moon/" target="_blank" rel="noreferrer">NASA Moon Trek <ExternalLink className="size-3" /></a>
            <a className="inline-flex items-center gap-1 text-signal hover:underline" href="https://ssd.jpl.nasa.gov/horizons/" target="_blank" rel="noreferrer">NASA JPL Horizons <ExternalLink className="size-3" /></a>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

/** An intentional default export so the page can be route-split. */
export default SciencePage
