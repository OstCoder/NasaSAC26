import { describe, expect, it } from 'vitest'
import { fromLeaflet, project, rhoForLat, toLeaflet, unproject } from './projection'

describe('south polar stereographic', () => {
  it('maps the pole to the origin', () => {
    const p = project(-90, 0)
    expect(p.x).toBeCloseTo(0)
    expect(p.y).toBeCloseTo(0)
  })
  it('puts 0° at the top and 90°E to the right', () => {
    expect(project(-85, 0).y).toBeGreaterThan(0)
    expect(project(-85, 90).x).toBeGreaterThan(0)
    expect(project(-85, -90).x).toBeLessThan(0)
  })
  it('round-trips', () => {
    for (const [lat, lon] of [[-89.45, -137.31], [-84.6, 31], [-86, 179.9], [-80, -45]]) {
      const back = unproject(project(lat, lon))
      expect(back.lat).toBeCloseTo(lat, 9)
      expect(back.lon).toBeCloseTo(lon, 9)
      const [la, ln] = toLeaflet(lat, lon)
      expect(fromLeaflet(la, ln).lat).toBeCloseTo(lat, 9)
    }
  })
  it('is close to true distance near the pole', () => {
    // 1° of latitude ≈ 30.32 km on a 1737.4 km sphere
    expect(rhoForLat(-89) - rhoForLat(-90)).toBeCloseTo(30.32, 1)
  })
})
