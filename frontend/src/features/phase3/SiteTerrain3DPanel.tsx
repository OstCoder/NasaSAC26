import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useApp } from '@/hooks/useAppContext'
import { useSiteDem, useSiteHorizon, useSiteSeries } from '@/hooks/useScenario'
import { fmtUtc } from '@/lib/format'
import type { SunDirection } from './terrainShadow'
import { terrainIllumination } from './terrainShadow'

const WINDOWS = [
  { key: 'initial', label: '1–8 Dec 2026' },
  { key: 'alternative', label: '11–18 Dec 2026' },
] as const
type WindowKey = (typeof WINDOWS)[number]['key']

const TerrainScene = React.lazy(() => import('./TerrainScene'))

const deg = (value: number) => (value * Math.PI) / 180

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

const meanAzEl = (records: { az: number; el: number }[] | null) => {
  if (!records || records.length === 0) return null
  const x = records.reduce((sum, point) => sum + Math.cos(deg(point.az)), 0)
  const y = records.reduce((sum, point) => sum + Math.sin(deg(point.az)), 0)
  const az = (Math.atan2(y, x) * 180) / Math.PI
  const el = records.reduce((sum, point) => sum + point.el, 0) / records.length
  return { az: (az + 360) % 360, el }
}

/**
 * Phase 5/6 experimental 3D terrain: the committed LOLA DEM around one
 * candidate, with the skyline on a sky dome, selected-time Sun/Earth
 * directions, a landing marker and a terrain ray-march shadow layer.
 *
 * The Three.js renderer is lazy-loaded only after the user enables the view,
 * so the planner's first paint does not pay for the 3D bundle.
 */
export function SiteTerrain3DPanel({
  siteId: requestedSiteId = null,
  sun: requestedSun = null,
  earth: requestedEarth = null,
  timestamp = null,
}: {
  siteId?: string | null
  sun?: SunDirection | null
  earth?: SunDirection | null
  timestamp?: string | null
} = {}) {
  const { features, sites } = useApp()
  const [enabled, setEnabled] = React.useState(false)
  const [siteId, setSiteId] = React.useState(requestedSiteId ?? sites[0]?.id ?? '')
  const [window, setWindow] = React.useState<WindowKey>('initial')
  const [exaggeration, setExaggeration] = React.useState(3)

  React.useEffect(() => {
    if (requestedSiteId && sites.some((site) => site.id === requestedSiteId)) {
      setSiteId(requestedSiteId)
    }
  }, [requestedSiteId, sites])

  const live = features.experimental_3d_terrain && enabled
  const dem = useSiteDem(siteId, live)
  const horizon = useSiteHorizon(siteId, window, live)
  const track = useSiteSeries(siteId, window, live)
  const error = dem.error ?? horizon.error ?? track.error

  const skyline = React.useMemo(() => {
    const profile = horizon.data?.terrain?.profile
    if (!profile) return []
    return profile.azimuth_deg.map((az, i) => ({ az, el: profile.elevation_deg[i] }))
  }, [horizon.data])

  const meanSun = React.useMemo(
    () => meanAzEl((track.data?.series ?? []).map((r) => ({ az: r.sun.azimuth_deg, el: r.sun.elevation_deg }))),
    [track.data],
  )
  const meanEarth = React.useMemo(
    () => meanAzEl((track.data?.series ?? []).map((r) => ({ az: r.earth.azimuth_deg, el: r.earth.elevation_deg }))),
    [track.data],
  )
  const sun = React.useMemo(
    () => (requestedSun ? { az: requestedSun.az, el: requestedSun.el } : meanSun),
    [requestedSun?.az, requestedSun?.el, meanSun],
  )
  const earth = React.useMemo(
    () => (requestedEarth ? { az: requestedEarth.az, el: requestedEarth.el } : meanEarth),
    [requestedEarth?.az, requestedEarth?.el, meanEarth],
  )

  const illumination = React.useMemo(
    () => (dem.data && sun
      ? terrainIllumination({ heights: dem.data.heights_m, cellM: dem.data.grid.cell_m }, sun)
      : null),
    [dem.data, sun],
  )

  const aria = dem.data
    ? `${dem.data.site.name}: pooled LOLA DEM, ${dem.data.grid.extent_m.east_west / 1000} km across at ${dem.data.grid.cell_m} m cells, heights exaggerated ${exaggeration}x. ${illumination ? `${Math.round(illumination.shadowFraction * 100)}% shadowed by the local terrain ray-march. ` : ''}Skyline maximum ${Math.max(...skyline.map((s) => s.el), 0).toFixed(2)} degrees.`
    : 'Site 3D terrain loading.'

  if (!features.experimental_3d_terrain) return null

  return (
    <Card>
      <CardHeader
        title="Site terrain in 3D (experimental)"
        description="LOLA heights around one candidate, relative to the pooled site cell and exaggerated for readability — a view, not a measurement. The 2D horizon profile stays the source of truth; the shadow layer is a local ray-march, not a PSR map."
      />
      <CardContent className="space-y-3">
        {!enabled ? (
          <p className="text-xs text-muted">
            Renders a 3D mesh of the committed site DEM (125 m pooled cells), the skyline,
            the selected-time Sun/Earth directions, a landing marker and modelled terrain shadows.
            Off by default.
            <Button size="sm" className="ml-2" onClick={() => setEnabled(true)}>Enable 3D view</Button>
          </p>
        ) : (
          <>
            {error && <ErrorNotice error={error} />}
            {!webglAvailable() && (
              <p className="text-xs text-sun">This browser cannot create a WebGL context, so the 3D view is unavailable. The 2D terrain profile remains available.</p>
            )}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <label className="text-muted" htmlFor="dem3d-site">Candidate</label>
              <select
                id="dem3d-site"
                className="rounded border border-rule-soft bg-panel px-2 py-1 text-xs text-ink"
                value={siteId}
                onChange={(e) => setSiteId(e.target.value)}
              >
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>{site.name}</option>
                ))}
              </select>
              <Tabs value={window} onValueChange={(v) => setWindow(v as WindowKey)}>
                <TabsList aria-label="Mission window">
                  {WINDOWS.map((w) => (
                    <TabsTrigger key={w.key} value={w.key}>{w.label}</TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
              <label className="ml-auto flex items-center gap-2 text-muted" htmlFor="dem3d-exag">
                Vertical exaggeration
                <input
                  id="dem3d-exag"
                  type="range" min={1} max={5} step={1} value={exaggeration}
                  onChange={(e) => setExaggeration(Number(e.target.value))}
                  className="w-28"
                />
                <span className="num text-ink">{exaggeration}x</span>
              </label>
            </div>
            {dem.data && !dem.error && webglAvailable() && (
              <div className="relative">
                <React.Suspense fallback={<p className="grid h-[360px] place-items-center text-xs text-muted">Loading the 3D renderer…</p>}>
                  <TerrainScene
                    dem={dem.data}
                    skyline={skyline}
                    sun={sun}
                    earth={earth}
                    exaggeration={exaggeration}
                    ariaLabel={aria}
                    illumination={illumination}
                  />
                </React.Suspense>
                <div className="pointer-events-none absolute left-2 bottom-2 rounded bg-night/85 px-2 py-1.5 text-[11px] leading-snug text-faint">
                  <p className="text-muted">Terrain shadow: local ray-march</p>
                  <p>{illumination ? `${Math.round(illumination.shadowFraction * 100)}% shadowed · ${illumination.rayLengthKm.toFixed(1)} km reach` : 'Sun direction unavailable'}</p>
                  <p>{dem.data.grid.cell_m} m cells · {(dem.data.grid.extent_m.east_west / 1000).toFixed(1)} km across · {exaggeration}x vertical</p>
                  <p className="text-signal">Blue marker: selected site cell</p>
                  {timestamp && <p className="num">{fmtUtc(timestamp)} UTC</p>}
                </div>
              </div>
            )}
            {dem.data && (
              <p className="text-xs text-faint" aria-live="polite">
                {aria} Source: {dem.data.source.file} (sha256 {dem.data.source.sha256.slice(0, 12)}…),
                heights {dem.data.height_convention.toLowerCase()}; the mesh shows metres relative
                to the pooled site cell ({dem.data.site_height_m.toFixed(0)} m above the sphere).
                {dem.data.grid.nodata_fill_cells > 0 && ` ${dem.data.grid.nodata_fill_cells} edge cells filled.`}
                {' '}Scene frame: x east, z south, y up; azimuth clockwise from local north.
                The next terrain-horizon calculation, not this display, determines official visibility.
              </p>
            )}
            {!dem.data && !error && (
              <p className="text-xs text-muted" role="status">Loading the pooled DEM…</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
