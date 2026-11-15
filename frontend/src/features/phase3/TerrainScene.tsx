import * as React from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { TerrainDem } from '@/types/api'
import type { SunDirection, TerrainIllumination } from './terrainShadow'

const KM = 1 / 1000
const DOME_R = 9
const deg = THREE.MathUtils.degToRad

function enuDirection(azimuthDeg: number, elevationDeg: number): THREE.Vector3 {
  const az = deg(azimuthDeg)
  const el = deg(elevationDeg)
  const horizontal = Math.cos(el)
  return new THREE.Vector3(
    Math.sin(az) * horizontal,
    Math.sin(el),
    -Math.cos(az) * horizontal,
  )
}

export interface TerrainSceneProps {
  dem: TerrainDem
  skyline: { az: number; el: number }[]
  sun: SunDirection | null
  earth: SunDirection | null
  exaggeration: number
  ariaLabel: string
  illumination: TerrainIllumination | null
  wireframe?: boolean
}

/** Lazy-loaded Three.js renderer. Kept separate from the panel's data hooks. */
export default function TerrainScene({
  dem, skyline, sun, earth, exaggeration, ariaLabel, illumination, wireframe = false,
}: TerrainSceneProps) {
  const mount = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const node = mount.current
    if (!node) return
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0d1524')
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 200)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1))
    node.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

    const size = dem.grid.size
    const ewKm = dem.grid.extent_m.east_west * KM
    const nsKm = dem.grid.extent_m.north_south * KM
    const geometry = new THREE.PlaneGeometry(ewKm, nsKm, size - 1, size - 1)
    geometry.rotateX(-Math.PI / 2)
    const position = geometry.attributes.position as THREE.BufferAttribute
    for (let row = 0; row < size; row++) {
      for (let col = 0; col < size; col++) {
        const index = row * size + col
        const height = (dem.heights_m[row][col] - dem.site_height_m) / 1000
        position.setY(index, height * exaggeration)
      }
    }
    position.needsUpdate = true
    geometry.computeVertexNormals()

    const colors = new Float32Array(position.count * 3)
    const dark = new THREE.Color('#101827')
    const lit = new THREE.Color('#9b865d')
    const neutral = new THREE.Color('#536177')
    for (let index = 0; index < position.count; index++) {
      const value = illumination ? illumination.values[index] : 0.65
      const color = illumination ? dark.clone().lerp(lit, value) : neutral.clone()
      colors[index * 3] = color.r
      colors[index * 3 + 1] = color.g
      colors[index * 3 + 2] = color.b
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    const material = new THREE.MeshStandardMaterial({
      vertexColors: true, roughness: 1, metalness: 0, wireframe,
    })
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    scene.add(new THREE.AmbientLight(0xffffff, 0.55))
    if (sun) {
      const direction = enuDirection(sun.az, sun.el)
      const light = new THREE.DirectionalLight(0xffe6bd, 0.9)
      light.position.copy(direction.multiplyScalar(12))
      scene.add(light)
    }

    if (skyline.length > 1) {
      const points = skyline.map((p) => enuDirection(p.az, p.el).multiplyScalar(DOME_R))
      const line = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({ color: '#8394b0' }),
      )
      scene.add(line)
    }

    const arrow = (color: string, dir: THREE.Vector3) => {
      const helper = new THREE.ArrowHelper(dir.normalize(), new THREE.Vector3(0, 0, 0), DOME_R * 0.85, color, DOME_R * 0.06, DOME_R * 0.03)
      scene.add(helper)
    }
    if (sun) arrow('#f2b544', enuDirection(sun.az, sun.el))
    if (earth) arrow('#4cc4e2', enuDirection(earth.az, earth.el))

    const cell = dem.grid.site_cell
    const markerX = (cell.col / (size - 1) - 0.5) * ewKm
    const markerZ = (cell.row / (size - 1) - 0.5) * nsKm
    const markerY = ((dem.heights_m[cell.row][cell.col] - dem.site_height_m) / 1000) * exaggeration
    const marker = new THREE.Mesh(
      new THREE.ConeGeometry(0.12, 0.42, 10),
      new THREE.MeshBasicMaterial({ color: '#6b9cff' }),
    )
    marker.position.set(markerX, markerY + 0.26, markerZ)
    scene.add(marker)
    const markerRing = new THREE.Mesh(
      new THREE.RingGeometry(0.16, 0.22, 20),
      new THREE.MeshBasicMaterial({ color: '#6b9cff', side: THREE.DoubleSide }),
    )
    markerRing.rotation.x = -Math.PI / 2
    markerRing.position.set(markerX, markerY + 0.01, markerZ)
    scene.add(markerRing)

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
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh
        mesh.geometry?.dispose()
        const objectMaterial = mesh.material
        if (Array.isArray(objectMaterial)) objectMaterial.forEach((item) => item.dispose())
        else objectMaterial?.dispose()
      })
      renderer.dispose()
      renderer.forceContextLoss()
      node.removeChild(renderer.domElement)
    }
  }, [dem, skyline, sun, earth, exaggeration, illumination, wireframe])

  return (
    <div className="relative h-[360px] w-full">
      <div ref={mount} className="h-full w-full" role="img" aria-label={ariaLabel} />
      <div className="pointer-events-none absolute left-3 top-3 rounded-md bg-night/70 px-2 py-1 text-[11px] text-muted backdrop-blur">
        <span className="font-medium text-ink">N</span>
        <span className="ml-1">↑</span>
        <span className="ml-2 text-faint">{(dem.grid.extent_m.east_west / 1000).toFixed(1)} km across</span>
      </div>
    </div>
  )
}
