import { CalendarPlus, GitCompare, Globe2, LoaderCircle, Map as MapIcon, X } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { ProvenanceStrip } from '@/components/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Select } from '@/components/ui/field'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LunarMap, type MapSelection, type Slot } from '@/features/lunar-map'
import {
  HorizonPanorama,
  MetricsTable,
  SnapshotPanel,
  VisibilityTimeline,
} from '@/features/visibility'
import { siteDraftLocation, useApp, type ScenarioDraft } from '@/hooks/useAppContext'
import { useScenario, useSnapshot } from '@/hooks/useScenario'
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

  const [viewer, setViewer] = React.useState<'map' | 'globe'>('map')
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
            title={viewer === 'globe' ? 'Lunar viewer' : 'South polar region'}
            description={
              viewer === 'globe'
                ? 'Lit by the Sun direction at the inspected time. Drag to rotate, scroll to zoom.'
                : 'Select a site, or click anywhere to analyse custom coordinates.'
            }
            actions={
              features.lunar_globe_3d && (
                <Tabs value={viewer} onValueChange={(v) => setViewer(v as 'map' | 'globe')}>
                  <TabsList aria-label="Viewer">
                    <TabsTrigger value="map"><MapIcon /> Polar map</TabsTrigger>
                    <TabsTrigger value="globe"><Globe2 /> 3D Moon</TabsTrigger>
                  </TabsList>
                </Tabs>
              )
            }
          />
          <CardContent className="space-y-3">
            {viewer === 'map' ? (
              <LunarMap
                className="aspect-square w-full"
                sites={sites}
                selections={{ A: selectionOf(draftA, sites), B: features.scenario_comparison ? selectionOf(draftB, sites) : undefined }}
                activeSlot={slot}
                imagery={imageryLayer ? { url: api.southPoleImageryUrl(imageryLayer, 2048, -80), credit: imageryCredit } : null}
                onImageryError={(url) => api.imageryError(url).then((e) => setImageryError(e?.message ?? 'Image failed to load.'))}
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
            ) : (
              <React.Suspense fallback={<div className="grid aspect-square w-full place-items-center text-sm text-muted">Loading 3D viewer…</div>}>
                <LunarGlobe
                  className="aspect-square w-full"
                  textureUrl={imageryLayer ? api.globalImageryUrl(imageryLayer, 2) : null}
                  textureCredit={imageryCredit}
                  sun={snapshot.data?.sun.sub_point ?? null}
                  earth={snapshot.data?.earth.sub_point ?? null}
                  site={selectionA ? { lat: selectionA.lat, lon: selectionA.lon, label: selectionA.label } : null}
                />
              </React.Suspense>
            )}

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
              {site?.coordinate_note && <p className="text-xs text-faint">Coordinates: {site.coordinate_note}</p>}
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
              <VisibilityTimeline result={result} index={safeIndex} onIndex={setIndex} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader
              title="Mission summary"
              description={<span className="num">{fmtUtc(result.landing_utc)} to {fmtUtc(result.end_utc)} UTC, sampled every {result.step_minutes} min with interpolated edges.</span>}
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
