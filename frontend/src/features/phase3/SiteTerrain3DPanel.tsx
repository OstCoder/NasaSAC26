import * as React from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useApp } from '@/hooks/useAppContext'
import { useSiteDem, useSiteHorizon, useSiteSeries } from '@/hooks/useScenario'
import type { TerrainDem } from '@/types/api'

const WINDOWS = [
  { key: 'initial', label: '1–8 Dec 2026' },
  { key: 'alternative', label: '11–18 Dec 2026' },
] as const
type WindowKey = (typeof WINDOWS)[number]['key']

const KM = 1 / 1000
/** Sky dome radius in scene units (scene x/z are km, y is exaggerated km). */
const DOME_R = 9

const deg = THREE.MathUtils.degToRad

/** Local ENU direction for an azimuth (deg clockwise from local north) and elevation (deg). */
function enuDirection(azimuthDeg: number, elevationDeg: number): THREE.Vector3 {
  const az = deg(azimuthDeg)
  const el = deg(elevationDeg)
  const horizontal = Math.cos(el)
  return new THREE.Vector3(
    Math.sin(az) * horizontal, // east
    Math.sin(el), // up
    -Math.cos(az) * horizontal, // north (scene z points south)
  )
}

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

function Scene({ dem, skyline, sun, earth, exaggeration, ariaLabel }: {
  dem: TerrainDem
  skyline: { az: number; el: number }[]
  sun: { az: number; el: number } | null
  earth: { az: number; el: number } | null
  exaggeration: number
  ariaLabel: string
}) {
  const mount = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const node = mount.current
    if (!node) return
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0d1524')
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 200)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    node.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

    // --- terrain mesh: x east (km), z south (km), y exaggerated metres -> km
    const size = dem.grid.size
    const ewKm = dem.grid.extent_m.east_west * KM
    const nsKm = dem.grid.extent_m.north_south * KM
    const geometry = new THREE.PlaneGeometry(ewKm, nsKm, size - 1, size - 1)
    geometry.rotateX(-Math.PI / 2) // plane in x/z, +y up; default plane: x -> +x, y -> -z
    const position = geometry.attributes.position as THREE.BufferAttribute
    for (let row = 0; row < size; row++) {
      for (let col = 0; col < size; col++) {
        const index = row * size + col
        // after rotateX(-90deg): plane row 0 (source top/north) sits at -z (north). Good.
        const height = (dem.heights_m[row][col] - dem.site_height_m) / 1000
        position.setY(index, height * exaggeration)
      }
    }
    position.needsUpdate = true
    geometry.computeVertexNormals()
    const material = new THREE.MeshStandardMaterial({ color: '#3b4a63', roughness: 0.9, metalness: 0 })
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    // lights: a dim ambient plus one aimed from the window's mean Sun direction
    scene.add(new THREE.AmbientLight(0xffffff, 0.45))

    // --- skyline curtain on the sky dome (directions rendered as directions)
    if (skyline.length > 1) {
      const points = skyline.map((p) => enuDirection(p.az, p.el).multiplyScalar(DOME_R))
      const line = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({ color: '#8394b0' }),
      )
      scene.add(line)
    }

    // --- Sun and Earth direction arrows (window-mean az/el)
    const arrow = (color: string, dir: THREE.Vector3) => {
      const helper = new THREE.ArrowHelper(dir.normalize(), new THREE.Vector3(0, 0, 0), DOME_R * 0.85, color, DOME_R * 0.06, DOME_R * 0.03)
      scene.add(helper)
    }
    if (sun) arrow('#f2b544', enuDirection(sun.az, sun.el))
    if (earth) arrow('#4cc4e2', enuDirection(earth.az, earth.el))

    camera.position.set(0, 9, 13)
    controls.target.set(0, 0, 0)
    controls.update()

    const resize = () => {
      const width = node.clientWidth
      const height = node.clientHeight
      renderer.setSize(width, height, false)
      camera.aspect = width / Math.max(height, 1)
      camera.updateProjectionMatrix()
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(node)

    let raf = 0
    const loop = () => {
      controls.update()
      renderer.render(scene, camera)
      raf = window.requestAnimationFrame(loop)
    }
    loop()

    return () => {
      window.cancelAnimationFrame(raf)
      observer.disconnect()
      controls.dispose()
      geometry.dispose()
      material.dispose()
      renderer.dispose()
      node.removeChild(renderer.domElement)
    }
  }, [dem, skyline, sun, earth, exaggeration])

  return <div ref={mount} className="h-[360px] w-full" role="img" aria-label={ariaLabel} />
}

const meanAzEl = (records: { az: number; el: number }[] | null) => {
  if (!records || records.length === 0) return null
  // circular mean of azimuth: the window can straddle 0/360
  const x = records.reduce((s, p) => s + Math.cos(deg(p.az)), 0)
  const y = records.reduce((s, p) => s + Math.sin(deg(p.az)), 0)
  const az = (Math.atan2(y, x) * 180) / Math.PI
  const el = records.reduce((s, p) => s + p.el, 0) / records.length
  return { az: (az + 360) % 360, el }
}

/**
 * Phase 4 Task 6 (experimental, feature-flagged, off by default): the LOLA DEM
 * around one candidate in 3D, with the committed skyline drawn on a sky dome
 * and the Sun/Earth window-mean directions as arrows. The 2D terrain horizon
 * profile and its numbers remain the source of truth; this mesh is display
 * only. Heights are LOLA metres above the reference sphere, shown relative to
 * the pooled site cell and exaggerated by a labelled factor.
 */
export function SiteTerrain3DPanel() {
  const { features, sites } = useApp()
  const [enabled, setEnabled] = React.useState(false)
  const [siteId, setSiteId] = React.useState(sites[0]?.id ?? '')
  const [window, setWindow] = React.useState<WindowKey>('initial')
  const [exaggeration, setExaggeration] = React.useState(3)

  const dem = useSiteDem(siteId)
  const horizon = useSiteHorizon(siteId, window)
  const track = useSiteSeries(siteId, window)
  const error = dem.error ?? horizon.error ?? track.error

  const skyline = React.useMemo(() => {
    const profile = horizon.data?.terrain?.profile
    if (!profile) return []
    return profile.azimuth_deg.map((az, i) => ({ az, el: profile.elevation_deg[i] }))
  }, [horizon.data])

  const sun = React.useMemo(
    () => meanAzEl((track.data?.series ?? []).map((r) => ({ az: r.sun.azimuth_deg, el: r.sun.elevation_deg }))),
    [track.data],
  )
  const earth = React.useMemo(
    () => meanAzEl((track.data?.series ?? []).map((r) => ({ az: r.earth.azimuth_deg, el: r.earth.elevation_deg }))),
    [track.data],
  )

  const aria = dem.data
    ? `${dem.data.site.name}: pooled LOLA DEM, ${dem.data.grid.extent_m.east_west / 1000} km across at ${dem.data.grid.cell_m} m cells, heights exaggerated ${exaggeration}x. Skyline maximum ${Math.max(...skyline.map((s) => s.el), 0).toFixed(2)} degrees.`
    : 'Site 3D terrain loading.'

  if (!features.experimental_3d_terrain) return null

  return (
    <Card>
      <CardHeader
        title="Site terrain in 3D (experimental)"
        description="LOLA heights around one candidate, relative to the pooled site cell and exaggerated for readability — a view, not a measurement. The 2D terrain horizon profile above stays the source of truth."
      />
      <CardContent className="space-y-3">
        {!enabled ? (
          <p className="text-xs text-muted">
            Renders a 3D mesh of the committed site DEM (125 m pooled cells), the skyline and the
            Sun/Earth window-mean directions. Off by default.
            <Button size="sm" className="ml-2" onClick={() => setEnabled(true)}>Enable 3D view</Button>
          </p>
        ) : (
          <>
            {error && <ErrorNotice error={error} />}
            {!webglAvailable() && (
              <p className="text-xs text-sun">This browser cannot create a WebGL context, so the 3D view is unavailable.</p>
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
              <Scene
                dem={dem.data}
                skyline={skyline}
                sun={sun}
                earth={earth}
                exaggeration={exaggeration}
                ariaLabel={aria}
              />
            )}
            {dem.data && (
              <p className="text-xs text-faint" aria-live="polite">
                {aria} Source: {dem.data.source.file} (sha256 {dem.data.source.sha256.slice(0, 12)}…),
                heights {dem.data.height_convention.toLowerCase()}; the mesh shows metres relative
                to the pooled site cell ({dem.data.site_height_m.toFixed(0)} m above the sphere).
                {dem.data.grid.nodata_fill_cells > 0 && ` ${dem.data.grid.nodata_fill_cells} edge cells filled.`}
                {' '}Scene frame: x east, z south, y up; azimuth clockwise from local north.
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
