/** Frontend-only presentation settings. Scientific settings live in config/lunanav.config.json. */
export const DURATION_PRESETS_HOURS = [24, 72, 168, 336, 708] as const

export const CHART_COLORS = {
  sun: '#f2b544',
  earth: '#4cc4e2',
  both: '#86dcc0',
  terrain: '#3b4a63',
  terrainEdge: '#6c7d9b',
  grid: '#213049',
  axis: '#5d6c87',
  cursor: '#6b9cff',
} as const

/** Optional imagery basemap in the same south-polar-stereographic km grid. See docs/ADAPTATION_GUIDE.md. */
export const LUNAR_TILE_URL: string | undefined = import.meta.env.VITE_LUNAR_TILE_URL as string | undefined
export const LUNAR_TILE_ATTRIBUTION: string =
  (import.meta.env.VITE_LUNAR_TILE_ATTRIBUTION as string | undefined) ?? 'NASA/GSFC/ASU LRO'
