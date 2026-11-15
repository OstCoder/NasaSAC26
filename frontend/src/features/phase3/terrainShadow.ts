/**
 * Illustrative terrain illumination for the pooled LOLA DEM.
 *
 * This is deliberately a small, deterministic ray-march, not a renderer
 * shadow map. For every DEM cell it:
 *   1. rejects a Sun below the geometric horizon;
 *   2. estimates the local surface normal from the four neighbours and rejects
 *      a facet facing away from the Sun;
 *   3. marches toward the Sun across the DEM (up to ~12 km) and checks whether
 *      any sampled terrain rises above the Sun ray.
 *
 * The result is a shading factor for the display. It is not the terrain-horizon
 * visibility calculation, which uses the committed 360-point LOLA skyline, and
 * it must never be used to classify a PSR.
 */

export interface SunDirection {
  az: number
  el: number
}

export interface ShadowTerrain {
  heights: number[][]
  cellM: number
}

export interface TerrainIllumination {
  /** Row-major shading factors in [0, 1]; 0 means the modelled terrain shadow. */
  values: Float32Array
  litFraction: number
  shadowFraction: number
  rayLengthKm: number
  cells: number
}

const rad = (degrees: number) => (degrees * Math.PI) / 180
const clamp01 = (value: number) => Math.min(1, Math.max(0, value))

function heightAt(heights: number[][], row: number, col: number): number {
  const r = Math.min(heights.length - 1, Math.max(0, Math.round(row)))
  const c = Math.min(heights[0].length - 1, Math.max(0, Math.round(col)))
  return heights[r][c]
}

/**
 * Compute the lighting state for every DEM cell.
 *
 * Row 0 is north and rows increase south, matching `SiteTerrain3DPanel`:
 * x/east is +col, z/south is +row. Azimuth is clockwise from north.
 */
export function terrainIllumination(
  terrain: ShadowTerrain,
  sun: SunDirection,
): TerrainIllumination {
  const heights = terrain.heights
  const rows = heights.length
  const cols = heights[0]?.length ?? 0
  const values = new Float32Array(rows * cols)
  if (rows === 0 || cols === 0) {
    return { values, litFraction: 0, shadowFraction: 0, rayLengthKm: 0, cells: 0 }
  }

  const elevation = sun.el
  if (!Number.isFinite(elevation) || elevation <= 0) {
    return { values, litFraction: 0, shadowFraction: 1, rayLengthKm: 0, cells: rows * cols }
  }

  const az = rad(sun.az)
  const east = Math.sin(az)
  const south = Math.cos(az)
  const tanElevation = Math.tan(rad(elevation))
  const cell = Math.max(1e-6, terrain.cellM)
  // At 125 m cells this is 96 steps ≈ 12 km. A farther ridge is left to the
  // committed skyline, which is the authoritative obstruction calculation.
  const maxSteps = Math.max(8, Math.min(96, Math.round(12_000 / cell)))
  let lit = 0

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const index = row * cols + col
      if (sun.el <= 0) continue

      // Local facet normal in east/north/up. North is row - 1.
      const gEast = (heightAt(heights, row, col + 1) - heightAt(heights, row, col - 1)) / (2 * cell)
      const gNorth = (heightAt(heights, row - 1, col) - heightAt(heights, row + 1, col)) / (2 * cell)
      const length = Math.hypot(gEast, gNorth, 1)
      const nx = -gEast / length
      const ny = -gNorth / length
      const nz = 1 / length
      const incidence = nx * east * Math.cos(rad(elevation))
        + ny * Math.cos(az) * Math.cos(rad(elevation))
        + nz * Math.sin(rad(elevation))
      if (incidence <= 0) continue

      const height = heights[row][col]
      let blocked = false
      for (let step = 1; step <= maxSteps; step++) {
        const sampleCol = col + east * step
        const sampleRow = row - south * step
        if (sampleRow < 0 || sampleRow > rows - 1 || sampleCol < 0 || sampleCol > cols - 1) break
        const rayHeight = height + tanElevation * step * cell
        if (heightAt(heights, sampleRow, sampleCol) > rayHeight + 0.05) {
          blocked = true
          break
        }
      }
      if (blocked) continue

      // Keep low-Sun flats visible while still distinguishing incidence.
      values[index] = clamp01(0.35 + 0.65 * incidence)
      lit++
    }
  }

  const cells = rows * cols
  return {
    values,
    litFraction: cells ? lit / cells : 0,
    shadowFraction: cells ? 1 - lit / cells : 0,
    rayLengthKm: (maxSteps * cell) / 1000,
    cells,
  }
}
