import { RotateCcw } from 'lucide-react'
import * as React from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Button } from '@/components/ui/button'
import { CHART_COLORS } from '@/config/app'
import { cn } from '@/lib/utils'
import type { SubPoint } from '@/types/api'

export interface LunarGlobeProps {
  /** Equirectangular texture URL (lon -180..180 left to right, north at top). */
  textureUrl: string | null
  textureCredit?: string
  sun: SubPoint | null
  earth: SubPoint | null
  site: { lat: number; lon: number; label: string } | null
  className?: string
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
  for (let lon = -180; lon <= 180; lon += 2) pts.push(moonDir(latDeg, lon).multiplyScalar(1.003))
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity }),
  )
  return line
}

/**
 * Interactive Moon: Moon Trek texture, lit from the JPL (or analytic) sub-solar
 * point at the inspected time, with the direction to Earth and the selected site.
 * The sphere is smooth: crater shadows from terrain are NOT rendered here, the
 * terrain-aware answer is the horizon panorama.
 */
export default function LunarGlobe({ textureUrl, textureCredit, sun, earth, site, className }: LunarGlobeProps) {
  const mountRef = React.useRef<HTMLDivElement>(null)
  const sceneRef = React.useRef<{
    renderer: THREE.WebGLRenderer
    camera: THREE.PerspectiveCamera
    controls: OrbitControls
    moon: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial>
    sunLight: THREE.DirectionalLight
    sunArrow: THREE.ArrowHelper
    earthMarker: THREE.Mesh
    earthLine: THREE.Line
    siteMarker: THREE.Mesh
  } | null>(null)
  const [textureState, setTextureState] = React.useState<'none' | 'loading' | 'ok' | 'error'>('none')

  // one-time scene setup
  React.useEffect(() => {
    const mount = mountRef.current!
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
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
      new THREE.SphereGeometry(1, 160, 120),
      new THREE.MeshStandardMaterial({ color: 0x9aa3b2, roughness: 1, metalness: 0 }),
    )
    scene.add(moon)
    scene.add(new THREE.AmbientLight(0xffffff, 0.06))
    const sunLight = new THREE.DirectionalLight(0xfff4e0, 2.6)
    scene.add(sunLight)

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

    sceneRef.current = { renderer, camera, controls, moon, sunLight, sunArrow, earthMarker, earthLine, siteMarker }

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
    new THREE.TextureLoader().load(
      textureUrl,
      (tex) => {
        if (!live) return tex.dispose()
        tex.colorSpace = THREE.SRGBColorSpace
        tex.anisotropy = s.renderer.capabilities.getMaxAnisotropy()
        s.moon.material.map?.dispose()
        s.moon.material.map = tex
        s.moon.material.color.set(0xffffff)
        s.moon.material.needsUpdate = true
        setTextureState('ok')
      },
      undefined,
      () => live && setTextureState('error'),
    )
    return () => {
      live = false
    }
  }, [textureUrl])

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
    } else s.sunArrow.visible = false
    if (earth) {
      const d = moonDir(earth.latitude_deg, earth.longitude_deg)
      s.earthMarker.position.copy(d.clone().multiplyScalar(1.8))
      s.earthLine.geometry.setFromPoints([d.clone().multiplyScalar(1.02), d.clone().multiplyScalar(1.73)])
      s.earthLine.computeLineDistances()
    }
    s.earthMarker.visible = s.earthLine.visible = Boolean(earth)
    if (site) s.siteMarker.position.copy(moonDir(site.lat, site.lon).multiplyScalar(1.004))
    s.siteMarker.visible = Boolean(site)
  }, [sun, earth, site])

  const resetView = React.useCallback(() => {
    const s = sceneRef.current
    if (!s) return
    const lon = site?.lon ?? 0
    // Oblique view over the south pole, from the site's meridian, whole disk in frame.
    s.camera.position.copy(moonDir(-50, lon).multiplyScalar(4.6))
    s.controls.target.set(0, 0, 0)
    s.camera.up.set(0, 1, 0)
    s.controls.update()
  }, [site?.lon])

  // initial camera; re-aim when the site changes
  React.useEffect(resetView, [resetView])

  return (
    <div className="space-y-1.5">
    <div className={cn('relative overflow-hidden rounded-md border border-rule-soft bg-[#070c15]', className)}>
      <div ref={mountRef} className="absolute inset-0" aria-label="Interactive 3D Moon. Drag to rotate, scroll to zoom." role="img" />
      <div className="pointer-events-none absolute top-2 left-2 z-10 space-y-1 rounded bg-night/80 px-2 py-1.5 text-xs text-muted">
        <p className="flex items-center gap-1.5"><i className="h-0.5 w-3 bg-sun" />Sunlight direction</p>
        <p className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-earth" />Earth direction (not to scale)</p>
        {site && <p className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-signal" />{site.label}</p>}
      </div>
      <Button size="sm" variant="secondary" className="absolute top-2 right-2 z-10" onClick={resetView}>
        <RotateCcw /> Reset view
      </Button>
    </div>
      <p className="text-[11px] leading-snug text-faint">
        {textureState === 'ok' && (textureCredit ?? 'Moon Trek imagery')}
        {textureState === 'loading' && 'Loading imagery from NASA/JPL Moon Trek…'}
        {textureState === 'error' && 'Imagery unavailable (Moon Trek not reachable). Lighting and directions are still shown.'}
        {textureState === 'none' && 'Imagery off.'}
        {' '}Smooth sphere: terrain shadows are not drawn here; see the horizon panorama.
      </p>
    </div>
  )
}
