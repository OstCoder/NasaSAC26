import { RotateCcw, Sun, SunDim } from 'lucide-react'
import * as React from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Button } from '@/components/ui/button'
import { CHART_COLORS } from '@/config/app'
import { cn } from '@/lib/utils'
import type { Crater, SubPoint } from '@/types/api'

export interface LunarGlobeProps {
  /** Equirectangular texture URL (lon -180..180 left to right, north at top). */
  textureUrl: string | null
  /** Sharper version of textureUrl, swapped in once it has loaded. */
  hdTextureUrl?: string | null
  textureCredit?: string
  /** LOLA-derived maps that give the sphere its real shape (see /api/imagery/relief). */
  relief?: { heightUrl: string; normalUrl: string; credit: string } | null
  sun: SubPoint | null
  earth: SubPoint | null
  site: { lat: number; lon: number; label: string } | null
  /** IAU named craters. Labels appear as each crater grows large enough on screen. */
  craters?: Crater[] | null
  /** Re-aims the camera at the sunlit side when it changes (e.g. switching to another time). */
  aimKey?: string
  /** Why sun/earth are missing (e.g. JPL Horizons unreachable). Shown instead of fake lighting. */
  positionNote?: string | null
  onTextureError?: () => void
  className?: string
}

/** Height map range in Moon radii: LOLA's ~19.9 km range, exaggerated 3x (keep in step with imagery.py). */
const RELIEF_SCALE = 0.034
/** Just above the highest displaced terrain, so markers never sink into it. */
const MARKER_RADIUS = 1 + RELIEF_SCALE / 2 + 0.003
const SUN_INTENSITY = 4.5
const MIN_LABEL_PX = 42
const MAX_LABELS = 30
const EVEN_LIGHT_INTENSITY = 3

/** True if this browser can create a WebGL context at all (hardware acceleration off, some VMs/managed laptops: false). */
function webglAvailable(): boolean {
  try {
    const c = document.createElement('canvas')
    return Boolean(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

/**
 * Moon body-fixed (x to 0°E, y to 90°E, z to north) -> three.js (y up).
 * (x, y, z) -> (x, z, -y) is a proper rotation, so handedness is preserved.
 */
function moonDir(latDeg: number, lonDeg: number): THREE.Vector3 {
  const la = THREE.MathUtils.degToRad(latDeg)
  const lo = THREE.MathUtils.degToRad(lonDeg)
  const x = Math.cos(la) * Math.cos(lo)
  const y = Math.cos(la) * Math.sin(lo)
  const z = Math.sin(la)
  return new THREE.Vector3(x, z, -y)
}

function latitudeRing(latDeg: number, color: string, opacity: number) {
  const pts: THREE.Vector3[] = []
  for (let lon = -180; lon <= 180; lon += 2) pts.push(moonDir(latDeg, lon).multiplyScalar(MARKER_RADIUS))
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity }),
  )
  return line
}

/**
 * Interactive Moon: Moon Trek texture, lit from the JPL (or analytic) sub-solar
 * point at the inspected time, with the direction to Earth and the selected site.
 * Its shape comes from LOLA elevation, exaggerated for display. Terrain does not
 * cast shadows here: the terrain-aware answer is the horizon panorama.
 */
export default function LunarGlobe(props: LunarGlobeProps) {
  const [glOk] = React.useState(webglAvailable)
  const [glError, setGlError] = React.useState<string | null>(null)
  if (!glOk || glError) {
    return (
      <div className={cn('grid place-items-center rounded-md border border-rule-soft bg-[#070c15] p-6 text-center', props.className)}>
        <div className="max-w-sm space-y-2 text-sm">
          <p className="font-medium text-ink">3D view needs WebGL, which this browser has turned off</p>
          <p className="text-muted">
            Turn on hardware acceleration (Chrome: Settings, System, "Use graphics acceleration when available"),
            then reload. Everything else in LunaNav works without it, including the polar map.
          </p>
          {glError && <p className="text-xs text-faint">{glError}</p>}
        </div>
      </div>
    )
  }
  return <GlobeScene {...props} onGlError={setGlError} />
}

function GlobeScene({
  textureUrl, hdTextureUrl, textureCredit, relief, sun, earth, site, craters, aimKey, positionNote, onTextureError, onGlError, className,
}: LunarGlobeProps & { onGlError: (msg: string) => void }) {
  const mountRef = React.useRef<HTMLDivElement>(null)
  const labelsRef = React.useRef<HTMLDivElement>(null)
  const updateLabelsRef = React.useRef<() => void>(() => {})
  const sceneRef = React.useRef<{
    renderer: THREE.WebGLRenderer
    camera: THREE.PerspectiveCamera
    controls: OrbitControls
    moon: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial>
    sunLight: THREE.DirectionalLight
    headLight: THREE.DirectionalLight
    sunArrow: THREE.ArrowHelper
    earthMarker: THREE.Mesh
    earthLine: THREE.Line
    siteMarker: THREE.Mesh
  } | null>(null)
  const [textureState, setTextureState] = React.useState<'none' | 'loading' | 'ok' | 'error'>('none')
  const [reliefState, setReliefState] = React.useState<'none' | 'loading' | 'ok' | 'error'>('none')
  const [evenLight, setEvenLight] = React.useState(false)

  // one-time scene setup
  React.useEffect(() => {
    const mount = mountRef.current!
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch (e) {
      onGlError(e instanceof Error ? e.message : String(e))
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 100)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.minDistance = 1.25
    controls.maxDistance = 8
    controls.enablePan = false

    const moon = new THREE.Mesh(
      new THREE.SphereGeometry(1, 512, 256),
      new THREE.MeshStandardMaterial({ color: 0x9aa3b2, roughness: 1, metalness: 0 }),
    )
    scene.add(moon)
    scene.add(new THREE.AmbientLight(0xffffff, 0.12))
    const sunLight = new THREE.DirectionalLight(0xfff4e0, 0)
    scene.add(sunLight)
    // Neutral light that follows the camera, used when no Sun position is available or the
    // user asks for even light, so the Moon stays visible without pretending to be real illumination.
    const headLight = new THREE.DirectionalLight(0xffffff, EVEN_LIGHT_INTENSITY)
    camera.add(headLight)
    scene.add(camera)

    scene.add(latitudeRing(-80, CHART_COLORS.terrainEdge, 0.7))
    scene.add(latitudeRing(-85, CHART_COLORS.terrainEdge, 0.45))

    const sunArrow = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 0.4,
      new THREE.Color(CHART_COLORS.sun).getHex(), 0.1, 0.05)
    scene.add(sunArrow)

    const earthMarker = new THREE.Mesh(
      new THREE.SphereGeometry(0.07, 32, 16),
      new THREE.MeshBasicMaterial({ color: CHART_COLORS.earth }),
    )
    scene.add(earthMarker)
    const earthLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(1, 0, 0)]),
      new THREE.LineDashedMaterial({ color: CHART_COLORS.earth, dashSize: 0.04, gapSize: 0.04, transparent: true, opacity: 0.7 }),
    )
    scene.add(earthLine)

    const siteMarker = new THREE.Mesh(
      new THREE.SphereGeometry(0.014, 16, 12),
      new THREE.MeshBasicMaterial({ color: CHART_COLORS.cursor }),
    )
    scene.add(siteMarker)

    sceneRef.current = { renderer, camera, controls, moon, sunLight, headLight, sunArrow, earthMarker, earthLine, siteMarker }

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = mount
      renderer.setSize(w, h, false)
      renderer.domElement.style.width = '100%'
      renderer.domElement.style.height = '100%'
      camera.aspect = w / Math.max(h, 1)
      camera.updateProjectionMatrix()
    }
    const ro = new ResizeObserver(resize)
    ro.observe(mount)
    resize()

    let raf = 0
    const loop = () => {
      controls.update()
      renderer.render(scene, camera)
      updateLabelsRef.current()
      raf = requestAnimationFrame(loop)
    }
    loop()

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      controls.dispose()
      scene.traverse((o) => {
        const m = o as THREE.Mesh
        m.geometry?.dispose?.()
        const mat = m.material as THREE.Material | THREE.Material[] | undefined
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose())
        else mat?.dispose?.()
      })
      moon.material.map?.dispose()
      moon.material.displacementMap?.dispose()
      moon.material.normalMap?.dispose()
      renderer.dispose()
      mount.removeChild(renderer.domElement)
      sceneRef.current = null
    }
  }, [])

  // texture
  React.useEffect(() => {
    const s = sceneRef.current
    if (!s || !textureUrl) {
      setTextureState('none')
      return
    }
    let live = true
    setTextureState('loading')
    const loader = new THREE.TextureLoader()
    const apply = (tex: THREE.Texture) => {
      tex.colorSpace = THREE.SRGBColorSpace
      tex.anisotropy = s.renderer.capabilities.getMaxAnisotropy()
      s.moon.material.map?.dispose()
      s.moon.material.map = tex
      s.moon.material.color.set(0xffffff)
      s.moon.material.needsUpdate = true
    }
    loader.load(
      textureUrl,
      (tex) => {
        if (!live) return tex.dispose()
        apply(tex)
        setTextureState('ok')
        if (hdTextureUrl) {
          // A missing HD texture is harmless: the standard one is already on screen.
          loader.load(hdTextureUrl, (hd) => (live ? apply(hd) : hd.dispose()))
        }
      },
      undefined,
      () => {
        if (!live) return
        setTextureState('error')
        onTextureError?.()
      },
    )
    return () => {
      live = false
    }
  }, [textureUrl, hdTextureUrl])

  // crater labels: one pooled element per crater, placed each frame from the 3D position
  React.useEffect(() => {
    const s = sceneRef.current
    const layer = labelsRef.current
    if (!s || !layer || !craters) return
    const items = [...craters]
      .sort((a, b) => b.diameter_km - a.diameter_km)
      .map((c) => {
        const el = document.createElement('span')
        el.textContent = c.name
        el.hidden = true
        el.className = 'absolute top-0 left-0 whitespace-nowrap text-[11px] text-[#dde5f0] [text-shadow:0_0_3px_#000,0_0_2px_#000]'
        layer.appendChild(el)
        return { el, dir: moonDir(c.latitude_deg, c.longitude_deg), diameter: c.diameter_km }
      })
    const toCamera = new THREE.Vector3()
    const p = new THREE.Vector3()
    updateLabelsRef.current = () => {
      const { clientWidth: w, clientHeight: h } = layer
      const dist = s.camera.position.length()
      // On-screen pixels per Moon radius, for a crater at the centre of the disk.
      const pxPerRadius = h / 2 / Math.tan(THREE.MathUtils.degToRad(s.camera.fov / 2)) / dist
      toCamera.copy(s.camera.position).normalize()
      let count = 0
      for (const it of items) {
        const facing = it.dir.dot(toCamera)
        const big = (it.diameter / 1737.4) * pxPerRadius * facing >= MIN_LABEL_PX
        const show = count < MAX_LABELS && big && facing > 1 / dist + 0.15
        it.el.hidden = !show
        if (!show) continue
        count++
        p.copy(it.dir).project(s.camera)
        it.el.style.transform = `translate(${((p.x + 1) / 2) * w}px, ${((1 - p.y) / 2) * h}px) translate(-50%, -50%)`
      }
    }
    return () => {
      updateLabelsRef.current = () => {}
      items.forEach((it) => it.el.remove())
    }
  }, [craters])

  // relief
  const heightUrl = relief?.heightUrl
  const normalUrl = relief?.normalUrl
  React.useEffect(() => {
    const s = sceneRef.current
    if (!s || !heightUrl || !normalUrl) {
      setReliefState('none')
      return
    }
    let live = true
    setReliefState('loading')
    const load = (url: string) => new THREE.TextureLoader().loadAsync(url)
    Promise.all([load(heightUrl), load(normalUrl)]).then(
      ([height, normal]) => {
        if (!live) {
          height.dispose()
          normal.dispose()
          return
        }
        height.wrapS = normal.wrapS = THREE.RepeatWrapping
        normal.anisotropy = s.renderer.capabilities.getMaxAnisotropy()
        const m = s.moon.material
        m.displacementMap = height
        m.displacementScale = RELIEF_SCALE
        m.displacementBias = -RELIEF_SCALE / 2
        m.normalMap = normal
        m.needsUpdate = true
        setReliefState('ok')
      },
      () => {
        if (live) setReliefState('error')
      },
    )
    return () => {
      live = false
    }
  }, [heightUrl, normalUrl])

  const realSun = Boolean(sun) && !evenLight

  // lighting + markers
  React.useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    if (sun) {
      const d = moonDir(sun.latitude_deg, sun.longitude_deg)
      s.sunLight.position.copy(d.clone().multiplyScalar(10))
      s.sunArrow.position.copy(d.clone().multiplyScalar(1.12))
      s.sunArrow.setDirection(d)
      s.sunArrow.visible = true
    } else {
      s.sunArrow.visible = false
    }
    s.sunLight.intensity = realSun ? SUN_INTENSITY : 0
    s.headLight.intensity = realSun ? 0 : EVEN_LIGHT_INTENSITY
    if (earth) {
      const d = moonDir(earth.latitude_deg, earth.longitude_deg)
      s.earthMarker.position.copy(d.clone().multiplyScalar(1.8))
      s.earthLine.geometry.setFromPoints([d.clone().multiplyScalar(MARKER_RADIUS), d.clone().multiplyScalar(1.73)])
      s.earthLine.computeLineDistances()
    }
    s.earthMarker.visible = s.earthLine.visible = Boolean(earth)
    if (site) s.siteMarker.position.copy(moonDir(site.lat, site.lon).multiplyScalar(MARKER_RADIUS))
    s.siteMarker.visible = Boolean(site)
  }, [sun, earth, site, realSun])

  // Read through a ref so scrubbing the timeline moves the light, not the camera.
  const sunLonRef = React.useRef<number | null>(null)
  React.useEffect(() => {
    sunLonRef.current = sun?.longitude_deg ?? null
  }, [sun?.longitude_deg])

  const resetView = React.useCallback(() => {
    const s = sceneRef.current
    if (!s) return
    // Oblique view of the sunlit side, whole disk in frame, south pole in view.
    const lon = sunLonRef.current ?? site?.lon ?? 0
    s.camera.position.copy(moonDir(-35, lon).multiplyScalar(4.6))
    s.controls.target.set(0, 0, 0)
    s.camera.up.set(0, 1, 0)
    s.controls.update()
  }, [site?.lon])

  // initial camera; re-aim when the site changes or the Sun position first arrives
  const hasSun = Boolean(sun)
  React.useEffect(resetView, [resetView, hasSun, aimKey])

  return (
    <div className="space-y-1.5">
    <div className={cn('relative overflow-hidden rounded-md border border-rule-soft bg-[#070c15]', className)}>
      <div ref={mountRef} className="absolute inset-0" aria-label="Interactive 3D Moon. Drag to rotate, scroll to zoom." role="img" />
      <div ref={labelsRef} aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden" />
      <div className="pointer-events-none absolute top-2 left-2 z-10 space-y-1 rounded bg-night/80 px-2 py-1.5 text-xs text-muted">
        {realSun && <p className="flex items-center gap-1.5"><i className="h-0.5 w-3 bg-sun" />Sunlight direction</p>}
        {earth && <p className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-earth" />Earth direction (not to scale)</p>}
        {site && <p className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-signal" />{site.label}</p>}
      </div>
      {!sun && (
        <div role="status" className="absolute inset-x-2 bottom-2 z-10 rounded-md border border-sun/40 bg-night/90 px-3 py-2 text-xs leading-relaxed text-muted">
          <span className="font-medium text-sun">No Sun position, so this lighting is neutral, not real.</span>{' '}
          {positionNote ?? 'Waiting for the calculation…'}
        </div>
      )}
      <div className="absolute top-2 right-2 z-10 flex flex-col items-end gap-1.5">
        <Button size="sm" variant="secondary" onClick={resetView}>
          <RotateCcw /> Reset view
        </Button>
        {sun && (
          <Button size="sm" variant="secondary" aria-pressed={evenLight} onClick={() => setEvenLight((v) => !v)}>
            {evenLight ? <Sun /> : <SunDim />} {evenLight ? 'Real sunlight' : 'Even light'}
          </Button>
        )}
      </div>
      {sun && evenLight && (
        <div role="status" className="absolute inset-x-2 bottom-2 z-10 rounded-md border border-rule-soft bg-night/90 px-3 py-2 text-xs text-muted">
          Even light for inspecting the surface. This is not the real illumination.
        </div>
      )}
    </div>
      <p className="text-[11px] leading-snug text-faint">
        {textureState === 'ok' && (textureCredit ?? 'Moon Trek imagery')}
        {textureState === 'loading' && 'Loading imagery from NASA/JPL Moon Trek…'}
        {textureState === 'error' && 'Imagery unavailable (see the message below). Showing a plain sphere.'}
        {textureState === 'none' && 'Imagery off.'}
        {reliefState === 'ok' && ` Shape: ${relief?.credit} Height exaggerated 3x.`}
        {reliefState === 'loading' && ' Loading LOLA elevation…'}
        {reliefState === 'error' && ' LOLA elevation unavailable, so this is a smooth sphere.'}
        {' '}Crater names: IAU gazetteer. Shadows in the imagery were captured by LRO and don't move; terrain casts no live shadows here, so see the horizon panorama for those.
      </p>
    </div>
  )
}
