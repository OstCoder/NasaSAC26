/**
 * Night side of the Moon on an equirectangular map, for a spherical Moon with no terrain.
 * The terminator is where the Sun's elevation is zero: tan(lat) = -cos(lon - sunLon) / tan(sunLat).
 * Returns a closed [lat, lon] ring along the terminator and around the pole in darkness.
 */
export function nightPolygon(sunLatDeg: number, sunLonDeg: number): [number, number][] {
  const rad = Math.PI / 180
  // At exactly 0° the terminator is two meridians; a tiny offset keeps the formula defined.
  const sunLat = Math.abs(sunLatDeg) < 0.01 ? 0.01 : sunLatDeg
  const ring: [number, number][] = []
  for (let lon = -180; lon <= 180; lon += 2) {
    const lat = Math.atan(-Math.cos((lon - sunLonDeg) * rad) / Math.tan(sunLat * rad)) / rad
    ring.push([lat, lon])
  }
  const darkPole = sunLat > 0 ? -90 : 90
  return [...ring, [darkPole, 180], [darkPole, -180]]
}

/**
 * Night side on the south polar map, as [lat, lon] rings for an even-odd fill.
 * South of 'edgeLat', each meridian is dark on one side of the terminator: toward the
 * pole when the Sun is north of the equator, toward the map's edge when it is south.
 */
export function polarNightRings(sunLatDeg: number, sunLonDeg: number, edgeLat = -80): [number, number][][] {
  const rad = Math.PI / 180
  const sunLat = Math.abs(sunLatDeg) < 0.01 ? 0.01 : sunLatDeg
  const terminator = (lon: number) => Math.atan(-Math.cos((lon - sunLonDeg) * rad) / Math.tan(sunLat * rad)) / rad
  const lons = Array.from({ length: 181 }, (_, i) => i * 2 - 180)
  if (sunLat > 0) return [lons.map((lon) => [Math.min(terminator(lon), edgeLat), lon])]
  return [lons.map((lon) => [edgeLat, lon]), lons.map((lon) => [Math.min(terminator(lon), edgeLat), lon])]
}
