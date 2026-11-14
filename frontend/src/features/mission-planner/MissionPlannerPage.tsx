import { CalendarPlus, Earth, GitCompare, Globe2, LoaderCircle, Map as MapIcon, X } from 'lucide-react'
import * as React from 'react'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ErrorNotice } from '@/components/ErrorNotice'
import { ProvenanceStrip } from '@/components/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Select } from '@/components/ui/field'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { GlobalMoonMap, LunarMap, type MapSelection, type Slot } from '@/features/lunar-map'
import {
  HorizonPanorama,
  MetricsTable,
  SnapshotPanel,
  VisibilityTimeline,
} from '@/features/visibility'
import { siteDraftLocation, useApp, type ScenarioDraft } from '@/hooks/useAppContext'
import { useCraters, useScenario, useSkyNow, useSnapshot } from '@/hooks/useScenario'
import { fmtLat, fmtLon, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import { ScenarioEditor } from './ScenarioEditor'
import { ProvenanceCallout } from './ProvenanceCallout'

function selectionOf(d: ScenarioDraft, sites: ReturnType<typeof useApp>['sites']): MapSelection | undefined {
  if (d.location.site_id) {
    const s = sites.find((x) => x.id === d.location.site_id)
    return s ? { lat: s.latitude_deg, lon: s.longitude_deg, label: s.name } : undefined
  }
  if (d.location.latitude_deg != null && d.location.longitude_deg != null)
    return { lat: d.location.latitude_deg, lon: d.location.longitude_deg, label: d.locationName }
  return undefined
}

const LunarGlobe = React.lazy(() => import('@/features/lunar-globe/LunarGlobe'))

type Viewer = 'map' | 'moon' | 'globe'

const VIEWER_TEXT: Record<Viewer, { title: string; description: string }> = {
  map: { title: 'South polar region', description: 'Select a site, or click anywhere to analyse custom coordinates. Crater outlines are from the IAU gazetteer.' },
  moon: { title: 'Whole Moon', description: 'Scroll to zoom into the LRO imagery. Crater names and outlines are from the IAU gazetteer.' },
  globe: { title: 'Lunar viewer', description: 'Drag to rotate, scroll to zoom.' },
}

const addDays = (iso: string, d: number) => new Date(Date.parse(iso) + d * 86_400_000).toISOString().slice(0, 19) + 'Z'

export function MissionPlannerPage({ onCompare }: { onCompare: () => void }) {
  const { sites, mode, setMode, features, config, draftA, setDraftA, draftB, setDraftB } = useApp()
  const [slot, setSlot] = React.useState<Slot>('A')
  const [index, setIndex] = React.useState(0)
  const [candidates, setCandidates] = React.useState<string[]>(() => [
    draftA.landing_utc,
    addDays(draftA.landing_utc, 7),
    addDays(draftA.landing_utc, 14),
  ])

  const scenario = useScenario(draftA, mode)
  const result = scenario.data
  const n = result?.series.times_utc.length ?? 0
  React.useEffect(() => setIndex(0), [result?.landing_utc, result?.location.name, n])
  const safeIndex = Math.min(index, Math.max(0, n - 1))
  const snapshotTime = result ? result.series.times_utc[safeIndex] : null
  const snapshot = useSnapshot(draftA, snapshotTime, mode)

  const site = draftA.location.site_id ? sites.find((s) => s.id === draftA.location.site_id) : undefined
  const setDraft = slot === 'A' ? setDraftA : setDraftB
  const selectionA = selectionOf(draftA, sites)

  const [viewer, setViewer] = React.useState<Viewer>('map')
  const craters = useCraters().data
  const skyNow = useSkyNow(mode)
  const [sunTime, setSunTime] = React.useState<'now' | 'mission'>('now')
  const live = sunTime === 'now'
  const shownSun = (live ? skyNow.data?.sun : snapshot.data?.sun.sub_point) ?? null
  const shownEarth = (live ? skyNow.data?.earth : snapshot.data?.earth.sub_point) ?? null
  const [imageryLayer, setImageryLayer] = React.useState<string>(features.lunar_imagery ? config.imagery.default_layer : '')
  const [imageryError, setImageryError] = React.useState<string | null>(null)
  const imageryCredit = imageryLayer ? (config.imagery.layers[imageryLayer]?.credit ?? '') : ''

  return (
    <div className="space-y-4">
      {result && <ProvenanceCallout provenance={result.provenance} />}

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-12">
        {/* Map / 3D viewer */}
        <Card className="min-w-0 lg:col-span-5">
          <CardHeader
            title={VIEWER_TEXT[viewer].title}
            description={VIEWER_TEXT[viewer].description}
            actions={
              <Tabs value={viewer} onValueChange={(v) => setViewer(v as Viewer)}>
                <TabsList aria-label="Viewer">
                  <TabsTrigger value="map"><MapIcon /> Polar map</TabsTrigger>
                  <TabsTrigger value="moon"><Earth /> Whole Moon</TabsTrigger>
                  {features.lunar_globe_3d && <TabsTrigger value="globe"><Globe2 /> 3D Moon</TabsTrigger>}
                </TabsList>
              </Tabs>
            }
          />
          <CardContent className="space-y-3">
            {viewer === 'map' ? (
              <LunarMap
                className="aspect-square w-full"
                sites={sites}
                selections={{ A: selectionOf(draftA, sites), B: features.scenario_comparison ? selectionOf(draftB, sites) : undefined }}
                activeSlot={slot}
                imagery={
                  imageryLayer
                    ? {
                        // 1024 covers the card at 2x density and renders 128 Trek tiles cold
                        // instead of 612 at 2048 (~6 s rather than ~24 s on a first load).
                        url: api.southPoleImageryUrl(imageryLayer, 1024, -80),
                        previewUrl: api.southPoleImageryUrl(imageryLayer, 512, -80),
                        credit: imageryCredit,
                      }
                    : null
                }
                onImageryError={(url) => api.imageryError(url).then((e) => setImageryError(e?.message ?? 'Image failed to load.'))}
                craters={craters}
                sun={shownSun}
                onSelectSite={(s, which) => (which === 'A' ? setDraftA : setDraftB)((d) => ({ ...d, ...siteDraftLocation(s) }))}
                onPickCoordinates={
                  features.custom_coordinates
                    ? (lat, lon) =>
                        setDraft((d) => ({
                          ...d,
                          location: { latitude_deg: +lat.toFixed(4), longitude_deg: +lon.toFixed(4) },
                          locationName: `Custom ${fmtLat(lat)} ${fmtLon(lon)}`,
                        }))
                    : undefined
                }
              />
            ) : viewer === 'moon' ? (
              <GlobalMoonMap
                className="aspect-[2/1] w-full"
                sites={sites}
                selection={selectionA}
                onSelectSite={(s) => setDraftA((d) => ({ ...d, ...siteDraftLocation(s) }))}
                tiles={imageryLayer ? { url: api.tileUrlTemplate(imageryLayer), maxNativeZoom: config.imagery.layers[imageryLayer]?.max_zoom ?? 6, credit: imageryCredit } : null}
                craters={craters}
                sun={shownSun}
                earth={shownEarth}
                onImageryError={(url) => api.imageryError(url).then((e) => setImageryError(e?.message ?? 'Image failed to load.'))}
              />
            ) : (
              <ErrorBoundary
                resetKey={imageryLayer + mode}
                fallback={(err, reset) => (
                  <div className="grid aspect-square w-full place-items-center rounded-md border border-rule-soft p-6 text-center text-sm">
                    <div className="max-w-sm space-y-2">
                      <p className="font-medium text-ink">The 3D viewer stopped</p>
                      <p className="text-muted">
                        {/Loading chunk|dynamically imported module|Failed to fetch/i.test(err.message)
                          ? 'Its code could not be downloaded, usually because the dev server restarted. Reload the page.'
                          : err.message}
                      </p>
                      <Button size="sm" onClick={reset}>Try again</Button>
                    </div>
                  </div>
                )}
              >
                <React.Suspense fallback={<div className="grid aspect-square w-full place-items-center text-sm text-muted">Loading 3D viewer…</div>}>
                  <LunarGlobe
                    className="aspect-square w-full"
                    textureUrl={imageryLayer ? api.globalImageryUrl(imageryLayer, 2) : null}
                    hdTextureUrl={imageryLayer ? api.globalImageryUrl(imageryLayer, 3) : null}
                    relief={features.lunar_imagery ? { heightUrl: api.reliefUrl('height', 2), normalUrl: api.reliefUrl('normal', 3), credit: config.imagery.layers[config.imagery.relief_layer]?.credit ?? '' } : null}
                    textureCredit={imageryCredit}
                    craters={craters}
                    aimKey={sunTime}
                    sun={shownSun}
                    earth={shownEarth}
                    positionNote={
                      live
                        ? skyNow.error?.message ?? (skyNow.loading ? 'Getting the Sun position…' : null)
                        : scenario.error?.message ?? snapshot.error?.message ??
                          (scenario.loading || snapshot.loading ? 'Calculating the Sun position…' : null)
                    }
                    onTextureError={() => {
                      const url = api.globalImageryUrl(imageryLayer, 2)
                      api.imageryError(url).then((e) => setImageryError(e?.message ?? 'Image failed to load.'))
                    }}
                    site={selectionA ? { lat: selectionA.lat, lon: selectionA.lon, label: selectionA.label } : null}
                  />
                </React.Suspense>
              </ErrorBoundary>
            )}

            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13px]">
              <div role="radiogroup" aria-label="Sunlight time" className="flex rounded-md border border-rule-soft p-0.5">
                {([['now', 'Sun now'], ['mission', 'Mission time']] as const).map(([value, label]) => (
                  <button key={value} role="radio" aria-checked={sunTime === value} onClick={() => setSunTime(value)}
                    className={cn('h-7 rounded px-2.5 font-medium', sunTime === value ? 'bg-sun/15 text-sun' : 'text-muted')}>
                    {label}
                  </button>
                ))}
              </div>
              <p role="status" className="min-w-0 text-xs text-muted">
                {live && skyNow.data && (
                  <span className="num">
                    Sun overhead at {fmtLat(skyNow.data.sun.latitude_deg)}, {fmtLon(skyNow.data.sun.longitude_deg)} at {fmtUtc(skyNow.data.time_utc)} UTC.
                    {' '}{skyNow.data.source}, updates each minute.
                  </span>
                )}
                {live && skyNow.error && <span className="text-alert">Live Sun position unavailable: {skyNow.error.message}</span>}
                {!live && snapshotTime && <span className="num">Sunlight at {fmtUtc(snapshotTime)} UTC, from the timeline.</span>}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
              {features.lunar_imagery && (
                <label className="flex items-center gap-2 text-[13px] text-muted">
                  Imagery
                  <Select className="h-8 w-auto py-0 text-[13px]" value={imageryLayer}
                    onChange={(e) => { setImageryLayer(e.target.value); setImageryError(null) }}>
                    <option value="">None</option>
                    {Object.entries(config.imagery.layers).map(([id, l]) => (
                      <option key={id} value={id}>{l.label}</option>
                    ))}
                  </Select>
                </label>
              )}
              {viewer === 'map' && features.scenario_comparison && (
                <div role="radiogroup" aria-label="Map selection target" className="flex rounded-md border border-rule-soft p-0.5">
                  {(['A', 'B'] as Slot[]).map((s) => (
                    <button key={s} role="radio" aria-checked={slot === s} onClick={() => setSlot(s)}
                      className={cn('h-7 rounded px-2.5 text-[13px] font-medium',
                        slot === s ? (s === 'A' ? 'bg-signal/20 text-signal' : 'bg-[#c79bff]/20 text-[#c79bff]') : 'text-muted')}>
                      Place {s}
                    </button>
                  ))}
                </div>
              )}
              {features.scenario_comparison && (
                <Button size="sm" className="ml-auto" onClick={onCompare}>
                  <GitCompare /> Compare A and B
                </Button>
              )}
            </div>
            {imageryError && imageryLayer && <p className="text-xs text-alert">Imagery: {imageryError}</p>}
            {features.scenario_comparison && (
              <p className="min-w-0 truncate text-[13px] text-muted">
                <span className="text-signal">A</span> {draftA.locationName} <span className="px-1 text-faint">vs</span>
                <span className="text-[#c79bff]">B</span> {draftB.locationName}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Scenario + snapshot */}
        <div className="flex min-w-0 flex-col gap-4 lg:col-span-7">
          <Card>
            <CardHeader
              title={draftA.locationName}
              description={
                site ? (
                  <span className="num">{fmtLat(site.latitude_deg)}, {fmtLon(site.longitude_deg)}. {site.description}</span>
                ) : draftA.location.latitude_deg != null ? (
                  <span className="num">{fmtLat(draftA.location.latitude_deg)}, {fmtLon(draftA.location.longitude_deg!)}</span>
                ) : null
              }
              actions={scenario.loading && <LoaderCircle className="size-4 animate-spin text-muted" aria-label="Calculating" />}
            />
            <CardContent className="space-y-3">
              <ScenarioEditor draft={draftA} onChange={setDraftA} />
              <div className="flex flex-wrap items-center gap-1.5 border-t border-rule-soft pt-3">
                <span className="mr-1 text-[13px] text-muted">Candidate dates</span>
                {candidates.map((c) => (
                  <span key={c} className={cn('inline-flex h-7 items-center rounded-md border text-xs',
                    c === draftA.landing_utc ? 'border-signal/60 bg-signal/10 text-ink' : 'border-rule text-muted')}>
                    <button className="num h-full px-2 hover:text-ink" onClick={() => setDraftA((d) => ({ ...d, landing_utc: c }))}>
                      {fmtUtc(c)}
                    </button>
                    <button aria-label={`Remove ${fmtUtc(c)}`} className="h-full pr-1.5 text-faint hover:text-ink"
                      onClick={() => setCandidates((cs) => cs.filter((x) => x !== c))}>
                      <X className="size-3" />
                    </button>
                  </span>
                ))}
                {!candidates.includes(draftA.landing_utc) && (
                  <Button size="sm" variant="ghost" onClick={() => setCandidates((cs) => [...cs, draftA.landing_utc].sort())}>
                    <CalendarPlus /> Save current date
                  </Button>
                )}
              </div>
              {site && (
                <div className="space-y-1">
                  <p className="text-xs text-faint">
                    {site.region} · elevation{' '}
                    {site.elevation_m != null ? `${Math.round(site.elevation_m)} m` : 'not yet recorded'}
                    {site.slope_deg != null && ` · slope ${site.slope_deg.toFixed(1)}°`} · source{' '}
                    {site.source || 'not yet recorded'} · nearest PSR{' '}
                    {site.nearest_psr
                      ? `${site.nearest_psr.label} (${site.nearest_psr.distance_km.toFixed(1)} km, ${Math.round(site.nearest_psr.area_km2)} km²)`
                      : 'not yet mapped'}
                  </p>
                  {site.coordinate_note && <p className="text-xs text-faint">Coordinates: {site.coordinate_note}</p>}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="flex-1">
            <CardHeader
              title="Conditions at the inspected time"
              description={snapshotTime ? <span className="num">{fmtUtc(snapshotTime)} UTC. Move the timeline cursor to inspect other times.</span> : undefined}
            />
            <CardContent>
              {scenario.error ? (
                <ErrorNotice error={scenario.error} onUseDemo={mode !== 'demo' ? () => setMode('demo') : undefined} />
              ) : snapshot.data ? (
                <div className={cn(snapshot.loading && 'opacity-70 transition-opacity')}>
                  <SnapshotPanel snapshot={snapshot.data} />
                </div>
              ) : snapshot.error ? (
                <ErrorNotice error={snapshot.error} />
              ) : (
                <p className="text-sm text-muted">Calculating…</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {result && !scenario.error && (
        <>
          {features.horizon_panorama && (
            <Card>
              <CardHeader
                title="Horizon panorama"
                description="Full 360° skyline from the site, with the Sun and Earth paths over the mission. Faint dots are hidden behind terrain or below the horizon. Elevation is exaggerated."
                actions={
                  <div className="flex gap-3 text-xs text-muted">
                    <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-sun" />Sun</span>
                    <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-earth" />Earth</span>
                    <span className="flex items-center gap-1.5"><i className="h-2 w-3 rounded-sm bg-terrain" />Terrain</span>
                  </div>
                }
              />
              <CardContent className={cn(result.horizon_mask.provenance === 'synthetic' && 'rounded-b-lg')}>
                <HorizonPanorama result={result} index={safeIndex} />
                <p className="mt-1 text-xs text-faint">Skyline source: {result.horizon_mask.source}. Azimuth measured clockwise from local north, which points toward the lunar equator.</p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader title="Visibility timeline" description="Hatched track means blocked. Click a band or the chart, drag the slider, or press play." />
            <CardContent>
              <VisibilityTimeline result={result} index={safeIndex} onIndex={(i) => { setIndex(i); setSunTime('mission') }} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader
              title="Mission summary"
              description={
                <span className="num">
                  {config.mission.name} · {config.mission.label}. {fmtUtc(result.landing_utc)} to{' '}
                  {fmtUtc(result.end_utc)} UTC, sampled every{' '}
                  {result.step_minutes} min with interpolated edges.
                </span>
              }
            />
            <CardContent className="space-y-4">
              <MetricsTable metrics={result.metrics} />
              <ProvenanceStrip provenance={result.provenance} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
