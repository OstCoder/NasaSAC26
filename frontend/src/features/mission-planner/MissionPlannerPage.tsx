import { CalendarPlus, ChevronDown, Earth, GitCompare, Globe2, Lightbulb, LoaderCircle, Map as MapIcon, Sparkles, Sun, X } from 'lucide-react'
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
import { Phase3Panel } from '@/features/phase3/Phase3Panel'
import { TerrainHorizonPanel } from '@/features/phase3/TerrainHorizonPanel'
import { EngineeringBudgetPanel } from '@/features/phase3/EngineeringBudgetPanel'
import { FeasibilityPanel } from '@/features/phase3/FeasibilityPanel'
import { RequirementTuner } from '@/features/phase3/RequirementTuner'
import { DelayComparisonPanel } from '@/features/phase3/DelayComparisonPanel'
import { SiteTerrain3DPanel } from '@/features/phase3/SiteTerrain3DPanel'
import { siteDraftLocation, useApp, type ScenarioDraft } from '@/hooks/useAppContext'
import { useDataSaver } from '@/hooks/useDataSaver'
import { useCraters, useScenario, useSkyNow, useSnapshot } from '@/hooks/useScenario'
import { fmtHours, fmtLat, fmtLon, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type { ScenarioResult } from '@/types/api'
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
  map: { title: 'South pole map', description: 'Pick a site, or click anywhere for custom coordinates. Gold outlines are mapped permanently shadowed regions.' },
  moon: { title: 'Whole Moon', description: 'Scroll to zoom into the LRO imagery. Crater names and outlines come from the IAU gazetteer.' },
  globe: { title: 'Moon in 3D', description: 'Drag to rotate, scroll to zoom.' },
}

const addDays = (iso: string, d: number) => new Date(Date.parse(iso) + d * 86_400_000).toISOString().slice(0, 19) + 'Z'

function metricValue(result: ScenarioResult, id: string) {
  return result.metrics.find((metric) => metric.id === id)
}

function shareText(metric: ReturnType<typeof metricValue>): string {
  if (!metric || metric.value == null) return '—'
  return `${metric.censored ? '≥' : ''}${Math.round(metric.value)}%`
}

function Outcome({ icon: Icon, tone, label, value, note }: {
  icon: typeof Sun
  tone: string
  label: string
  value: string
  note: string
}) {
  return (
    <div className="rounded-md border border-rule-soft bg-night/40 p-3">
      <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-faint">
        <Icon className={cn('size-4', tone)} aria-hidden /> {label}
      </p>
      <p className="mt-2 font-display text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{note}</p>
    </div>
  )
}

function AtAGlance({ result }: { result: ScenarioResult }) {
  const sun = metricValue(result, 'sun_visible_pct')
  const earth = metricValue(result, 'earth_visible_pct')
  const blackout = metricValue(result, 'longest_earth_blackout_hours')
  const blackoutText = blackout?.value == null
    ? '—'
    : `${blackout.censored ? '≥' : ''}${Math.round(blackout.value)} h`

  return (
    <Card className="border-signal/30">
      <CardHeader
        title="Mission summary"
        description={
          <span className="num">
            {result.location.name} · {fmtUtc(result.landing_utc)} to {fmtUtc(result.end_utc)} UTC ·{' '}
            {fmtHours(result.duration_hours)} · sampled every {result.step_minutes} min
          </span>
        }
      />
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <Outcome
            icon={Sun}
            tone="text-sun"
            label="Sunlight"
            value={shareText(sun)}
            note="Share of the mission with the Sun above the landing-site horizon."
          />
          <Outcome
            icon={Earth}
            tone="text-earth"
            label="Earth in view"
            value={shareText(earth)}
            note="Share of the mission with Earth above the horizon."
          />
          <Outcome
            icon={X}
            tone="text-alert"
            label="Longest Earth blackout"
            value={blackoutText}
            note="Longest stretch without a direct view of Earth."
          />
        </div>
        <p className="text-xs leading-relaxed text-muted">
          These are visibility measurements. Sunlight is not generated power, and Earth in view is
          line of sight, not a working radio link. The timeline below shows exactly when each changes.
        </p>
      </CardContent>
    </Card>
  )
}

function StartHere({ onExample }: { onExample: () => void }) {
  const steps = [
    ['Pick a place', 'Choose a published candidate or click anywhere on the map.'],
    ['Choose a date', 'The two mission dates are one click away.'],
    ['Read the answer', 'Check sunlight, Earth contact and the timeline.'],
  ]
  return (
    <section aria-labelledby="start-here-title" className="rounded-xl border border-signal/30 bg-signal/5 p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-signal">
            <Lightbulb className="size-4" aria-hidden /> Start here
          </p>
          <h1 id="start-here-title" className="mt-1 max-w-[46ch] font-display text-xl font-semibold text-ink sm:text-2xl">
            Pick a landing site and a date. See when it gets sunlight and can reach Earth.
          </h1>
          <p className="mt-1 max-w-[65ch] text-sm text-muted">
            LunaNav does the comparison for you. There is no data setting to choose and no setup to learn.
          </p>
        </div>
        <Button onClick={onExample} className="shrink-0">
          <Sparkles /> Try the example
        </Button>
      </div>
      <ol className="mt-4 grid gap-3 md:grid-cols-3">
        {steps.map(([title, text], index) => (
          <li key={title} className="flex gap-2.5 rounded-md border border-rule-soft bg-night/30 p-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-signal/15 text-xs font-semibold text-signal" aria-hidden>
              {index + 1}
            </span>
            <span>
              <span className="block text-sm font-medium text-ink">{title}</span>
              <span className="block text-xs leading-relaxed text-muted">{text}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

export function MissionPlannerPage({ onCompare }: { onCompare: () => void }) {
  const { sites, mode, features, config, draftA, setDraftA, draftB, setDraftB } = useApp()
  const [slot, setSlot] = React.useState<Slot>('A')
  const [showAdvanced, setShowAdvanced] = React.useState(false)
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
  const [showPsrs, setShowPsrs] = React.useState(true)
  const imageryCredit = imageryLayer ? (config.imagery.layers[imageryLayer]?.credit ?? '') : ''
  const [dataSaver] = useDataSaver()
  const imagerySize = dataSaver ? 512 : 1024

  const [copied, setCopied] = React.useState(false)
  const [savedScenarios, setSavedScenarios] = React.useState<{ name: string; siteId: string; landing: string; duration: number }[]>(() => {
    try { return JSON.parse(localStorage.getItem('lunanav.savedScenarios') ?? '[]') } catch { return [] }
  })
  const persistSaved = (next: { name: string; siteId: string; landing: string; duration: number }[]) => {
    setSavedScenarios(next)
    try { localStorage.setItem('lunanav.savedScenarios', JSON.stringify(next)) } catch { /* ignore */ }
  }
  const saveScenario = () => {
    if (!draftA.location.site_id) return
    const name = window.prompt('Name this scenario')?.trim()
    if (!name) return
    persistSaved([...savedScenarios.filter((s) => s.name !== name), { name, siteId: draftA.location.site_id, landing: draftA.landing_utc, duration: draftA.duration_hours }])
  }
  const loadScenario = (name: string) => {
    const s = savedScenarios.find((x) => x.name === name)
    if (!s) return
    const site = sites.find((x) => x.id === s.siteId)
    setDraftA({ location: { site_id: s.siteId }, locationName: site?.name ?? s.siteId, landing_utc: s.landing, duration_hours: s.duration })
  }
  const deleteScenario = (name: string) => persistSaved(savedScenarios.filter((s) => s.name !== name))
  const shareUrl = React.useMemo(() => {
    if (!draftA.location.site_id) return null
    try {
      const u = new URL(window.location.href)
      u.search = ''
      u.searchParams.set('site', draftA.location.site_id)
      u.searchParams.set('landing', draftA.landing_utc)
      u.searchParams.set('duration', String(draftA.duration_hours))
      u.hash = 'planner'
      return u.toString()
    } catch {
      return null
    }
  }, [draftA])

  const exportCsv = React.useCallback(() => {
    if (!result) return
    const s = result.series
    const rows: string[] = []
    rows.push(['time_utc', 'sun_az_deg', 'sun_el_deg', 'sun_horizon_deg', 'sun_visible', 'earth_az_deg', 'earth_el_deg', 'earth_horizon_deg', 'earth_visible'].join(','))
    for (let i = 0; i < s.times_utc.length; i++) {
      rows.push([s.times_utc[i], s.sun_azimuth_deg[i], s.sun_elevation_deg[i], s.sun_terrain_horizon_deg[i], s.sun_visible[i], s.earth_azimuth_deg[i], s.earth_elevation_deg[i], s.earth_terrain_horizon_deg[i], s.earth_visible[i]].join(','))
    }
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `lunanav-${result.location.site_id ?? 'site'}-${result.landing_utc.slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [result])

  const copyLink = React.useCallback(async () => {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard unavailable */
    }
  }, [shareUrl])

  React.useEffect(() => {
    const on = () => { copyLink() }
    window.addEventListener('lunanav:copy-link', on)
    return () => window.removeEventListener('lunanav:copy-link', on)
  }, [copyLink])

  const tryExample = () => {
    const example = sites.find((s) => s.id === 'de-gerlache-rim') ?? sites[0]
    if (!example) return
    setDraftA({
      location: { site_id: example.id },
      locationName: example.name,
      landing_utc: config.simulation.default_landing_utc,
      duration_hours: config.simulation.default_duration_hours,
    })
    setSlot('A')
    window.setTimeout(() => {
      document.getElementById('mission-workspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 60)
  }

  return (
    <div className="space-y-4">
      <span className="sr-only" aria-live="polite" aria-atomic="true">
        {scenario.loading ? 'Calculating visibility…' : result ? 'Visibility data ready.' : ''}
      </span>
      <StartHere onExample={tryExample} />
      {result && <ProvenanceCallout provenance={result.provenance} />}
      <div className="flex flex-wrap items-center justify-end gap-2">
        {savedScenarios.length > 0 && (
          <select
            className="h-8 rounded-md border border-rule-soft bg-panel px-2 text-xs text-muted"
            defaultValue=""
            onChange={(e) => { if (e.target.value) loadScenario(e.target.value); e.target.value = '' }}
            aria-label="Load saved scenario"
          >
            <option value="" disabled>Load saved…</option>
            {savedScenarios.map((s) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </select>
        )}
        {savedScenarios.length > 0 && (
          <button
            type="button"
            onClick={() => { const n = window.prompt('Delete which scenario? ' + savedScenarios.map((s) => s.name).join(', ')); if (n) deleteScenario(n) }}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-rule-soft px-2.5 text-xs text-muted transition-colors hover:text-ink"
          >
            Delete
          </button>
        )}
        <button
          type="button"
          onClick={saveScenario}
          disabled={!draftA.location.site_id}
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-rule-soft px-2.5 text-xs text-muted transition-colors hover:text-ink disabled:opacity-50"
        >
          Save scenario
        </button>
        <button
          type="button"
          onClick={copyLink}
          disabled={!shareUrl}
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-rule-soft px-2.5 text-xs text-muted transition-colors hover:text-ink disabled:opacity-50"
        >
          {copied ? 'Copied!' : 'Copy scenario link'}
        </button>
        <button
          type="button"
          onClick={exportCsv}
          disabled={!result}
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-rule-soft px-2.5 text-xs text-muted transition-colors hover:text-ink disabled:opacity-50"
        >
          Export CSV
        </button>
      </div>

      <div id="mission-workspace" className="grid scroll-mt-20 grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-12">
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
                        url: api.southPoleImageryUrl(imageryLayer, imagerySize, -80),
                        previewUrl: api.southPoleImageryUrl(imageryLayer, 512, -80),
                        credit: imageryCredit,
                      }
                    : null
                }
                onImageryError={(url) => api.imageryError(url).then((e) => setImageryError(e?.message ?? 'Image failed to load.'))}
                craters={craters}
                sun={shownSun}
                showPsrs={showPsrs}
                highlightPsrId={site?.nearest_psr?.psr_id ?? null}
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
                    hdTextureUrl={dataSaver ? null : (imageryLayer ? api.globalImageryUrl(imageryLayer, 3) : null)}
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
              <label className="flex items-center gap-2 text-[13px] text-muted">
                <input type="checkbox" checked={showPsrs} onChange={(e) => setShowPsrs(e.target.checked)} />
                Shadow regions
              </label>
              {features.lunar_imagery && (
                <label className="flex items-center gap-2 text-[13px] text-muted">
                  Moon imagery
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
                      Choose {s}
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
                <p className="text-xs text-faint">
                  {site.region} · {site.elevation_m != null ? `${Math.round(site.elevation_m)} m elevation` : 'elevation not recorded'}
                  {site.nearest_psr && <> · nearest mapped PSR {site.nearest_psr.label} ({site.nearest_psr.distance_km.toFixed(1)} km)</>}
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="flex-1">
            <CardHeader
              title="Conditions at the selected time"
              description={snapshotTime ? <span className="num">{fmtUtc(snapshotTime)} UTC. Move the timeline cursor to inspect other times.</span> : undefined}
            />
            <CardContent>
              {scenario.error ? (
                <ErrorNotice
                  error={scenario.error}
                  onRetry={() => { scenario.retry(); snapshot.retry() }}
                />
              ) : snapshot.data ? (
                <div className={cn(snapshot.loading && 'opacity-70 transition-opacity')}>
                  <SnapshotPanel snapshot={snapshot.data} />
                </div>
              ) : snapshot.error ? (
                <ErrorNotice error={snapshot.error} onRetry={snapshot.retry} />
              ) : (
                <p className="text-sm text-muted">Calculating…</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {result && !scenario.error && (
        <>
          <AtAGlance result={result} />

          {features.horizon_panorama && (
            <Card>
              <CardHeader
                title="Horizon panorama"
                description={
                  result.horizon_mask.provenance === 'geometric_only'
                    ? 'No local terrain profile covers this point, so the skyline is the flat geometric horizon. The Sun and Earth paths are still shown over the mission.'
                    : 'Full 360° skyline from the site, with the Sun and Earth paths over the mission. Faint dots are hidden behind terrain or below the horizon. Elevation is exaggerated.'
                }
                actions={
                  <div className="flex gap-3 text-xs text-muted">
                    <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-sun" />Sun</span>
                    <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-earth" />Earth</span>
                    <span className="flex items-center gap-1.5"><i className="h-2 w-3 rounded-sm bg-terrain" />Skyline</span>
                  </div>
                }
              />
              <CardContent>
                <HorizonPanorama result={result} index={safeIndex} />
                <p className="mt-1 text-xs text-faint">
                  Skyline source: {result.horizon_mask.source}. Azimuth is measured clockwise from local north.
                </p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader title="Visibility timeline" description="Hatched track means blocked. Click the chart, drag the slider, or press play." />
            <CardContent>
              <VisibilityTimeline result={result} index={safeIndex} onIndex={(i) => { setIndex(i); setSunTime('mission') }} />
            </CardContent>
          </Card>
        </>
      )}

      <section className="rounded-xl border border-rule-soft bg-panel">
        <button
          type="button"
          aria-expanded={showAdvanced}
          aria-controls="advanced-analysis"
          onClick={() => setShowAdvanced((open) => !open)}
          className="flex w-full items-center justify-between gap-3 p-4 text-left"
        >
          <span>
            <span className="block font-display text-sm font-semibold text-ink">Advanced analysis</span>
            <span className="mt-0.5 block text-xs text-muted">
              Power and link budgets, mission requirements, landing-date comparison and 3D terrain.
            </span>
          </span>
          <ChevronDown className={cn('size-5 shrink-0 text-muted transition-transform', showAdvanced && 'rotate-180')} aria-hidden />
        </button>
      </section>

      {showAdvanced && (
        <div id="advanced-analysis" className="space-y-4">
          {result && !scenario.error && (
            <Card>
              <CardHeader
                title="Detailed measurements"
                description="Every visibility measure for this mission, including totals, blackouts and counts."
              />
              <CardContent className="space-y-4">
                <MetricsTable metrics={result.metrics} />
                <ProvenanceStrip provenance={result.provenance} />
              </CardContent>
            </Card>
          )}
          <Phase3Panel />
          <TerrainHorizonPanel />
          <EngineeringBudgetPanel />
          <FeasibilityPanel />
          <RequirementTuner />
          <DelayComparisonPanel />
          <SiteTerrain3DPanel
            siteId={site?.id ?? null}
            sun={snapshot.data ? { az: snapshot.data.sun.azimuth_deg, el: snapshot.data.sun.elevation_deg } : null}
            earth={snapshot.data ? { az: snapshot.data.earth.azimuth_deg, el: snapshot.data.earth.elevation_deg } : null}
            timestamp={snapshotTime}
          />
        </div>
      )}
    </div>
  )
}
