import type { BodyState } from '@/types/api'

/** Three distinct states: never collapse "blocked by terrain" into "below horizon". */
export function bodyStatus(s: Pick<BodyState, 'elevation_deg' | 'visible'>): {
  label: string
  tone: 'visible' | 'terrain' | 'below'
} {
  if (s.visible) return { label: 'Above terrain horizon', tone: 'visible' }
  if (s.elevation_deg > 0) return { label: 'Blocked by terrain', tone: 'terrain' }
  return { label: 'Below geometric horizon', tone: 'below' }
}
