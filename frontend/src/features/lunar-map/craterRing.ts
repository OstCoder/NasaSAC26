const MOON_RADIUS_KM = 1737.4

/**
 * True circle on the sphere, as a [lat, lon] ring for the equirectangular map.
 * Longitude is unwrapped around the centre, so a crater crossing 180° stays in one piece.
 */
export function craterRing(latDeg: number, lonDeg: number, diameterKm: number, points = 36): [number, number][] {
  const rad = Math.PI / 180
  const angular = diameterKm / 2 / MOON_RADIUS_KM
  const lat = latDeg * rad
  return Array.from({ length: points }, (_, i) => {
    const bearing = (i / points) * 2 * Math.PI
    const sinLat = Math.sin(lat) * Math.cos(angular) + Math.cos(lat) * Math.sin(angular) * Math.cos(bearing)
    const dLon = Math.atan2(
      Math.sin(bearing) * Math.sin(angular) * Math.cos(lat),
      Math.cos(angular) - Math.sin(lat) * sinLat,
    )
    return [Math.asin(sinLat) / rad, lonDeg + dLon / rad]
  })
}
