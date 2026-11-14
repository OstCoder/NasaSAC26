import type { Crater, Site, SubPoint } from '@/types/api'

export type Slot = 'A' | 'B'

export interface MapSelection {
  lat: number
  lon: number
  label: string
}

/**
 * Contract every lunar map implementation honours. The 2D polar map is one
 * implementation; a future 3D terrain view can implement the same props and
 * be swapped in from features/lunar-map/index.ts.
 */
export interface LunarMapProps {
  sites: Site[]
  selections: Partial<Record<Slot, MapSelection>>
  activeSlot: Slot
  onSelectSite: (site: Site, slot: Slot) => void
  /** Present only when custom coordinates are enabled. */
  onPickCoordinates?: (lat: number, lon: number, slot: Slot) => void
  /** South-polar-stereographic image covering 80°S to the pole (see /api/imagery/south-pole). */
  imagery?: { url: string; previewUrl?: string; credit: string } | null
  onImageryError?: (url: string) => void
  /** IAU named craters, drawn when big enough at the current zoom. */
  craters?: Crater[] | null
  /** Sub-solar point used to shade the night side. */
  sun?: SubPoint | null
  className?: string
}

/** Whole-Moon equirectangular map. Sites are selected here, custom coordinates only on the polar map. */
export interface GlobalMoonMapProps {
  sites: Site[]
  selection?: MapSelection
  onSelectSite: (site: Site) => void
  /** Leaflet URL template with {z}, {y} (row) and {x} (column); see /api/imagery/tile. */
  tiles?: { url: string; maxNativeZoom: number; credit: string } | null
  sun?: SubPoint | null
  earth?: SubPoint | null
  craters?: Crater[] | null
  onImageryError?: (tileUrl: string) => void
  className?: string
}
