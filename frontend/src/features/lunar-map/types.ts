import type { Site } from '@/types/api'

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
  imagery?: { url: string; credit: string } | null
  onImageryError?: (url: string) => void
  className?: string
}
