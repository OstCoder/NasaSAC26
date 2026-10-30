/**
 * South polar stereographic projection on the IAU mean lunar sphere.
 *
 * Map plane (km), viewed from outside the Moon above the south pole:
 *   x = rho * sin(lon)    (90°E to the right)
 *   y = rho * cos(lon)    (0°, the Earth-facing meridian, at the top)
 *   rho = 2R * tan((90° + lat) / 2)
 *
 * Leaflet uses a CRS.Simple plane, so LatLng(y, x) carries projected km, NOT
 * selenographic degrees. Always go through project()/unproject().
 * Scale error is < 0.2% poleward of 85°S and ~0.8% at 80°S.
 */
export const MOON_RADIUS_KM = 1737.4

export interface XY {
  x: number
  y: number
}

const rad = (d: number) => (d * Math.PI) / 180
const deg = (r: number) => (r * 180) / Math.PI

export function project(latDeg: number, lonDeg: number): XY {
  const rho = 2 * MOON_RADIUS_KM * Math.tan(rad(90 + latDeg) / 2)
  return { x: rho * Math.sin(rad(lonDeg)), y: rho * Math.cos(rad(lonDeg)) }
}

export function unproject({ x, y }: XY): { lat: number; lon: number } {
  const rho = Math.hypot(x, y)
  const lat = -90 + 2 * deg(Math.atan(rho / (2 * MOON_RADIUS_KM)))
  const lon = rho === 0 ? 0 : deg(Math.atan2(x, y))
  return { lat, lon: ((lon + 540) % 360) - 180 }
}

export function rhoForLat(latDeg: number): number {
  return 2 * MOON_RADIUS_KM * Math.tan(rad(90 + latDeg) / 2)
}

/** Leaflet [lat, lng] tuple for the CRS.Simple plane. */
export function toLeaflet(latDeg: number, lonDeg: number): [number, number] {
  const p = project(latDeg, lonDeg)
  return [p.y, p.x]
}

export function fromLeaflet(lat: number, lng: number): { lat: number; lon: number } {
  return unproject({ x: lng, y: lat })
}
