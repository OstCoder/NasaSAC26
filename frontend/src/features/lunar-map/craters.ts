/**
 * Approximate crater outlines for orientation only (centre lat/lon in degrees,
 * diameter in km), rounded from the IAU Gazetteer of Planetary Nomenclature.
 * Replace with LOLA/LROC imagery tiles for anything quantitative.
 */
export interface CraterRef {
  name: string
  lat: number
  lon: number
  diameterKm: number
}

export const SOUTH_POLE_CRATERS: CraterRef[] = [
  { name: 'Shackleton', lat: -89.67, lon: 129.78, diameterKm: 21 },
  { name: 'de Gerlache', lat: -88.5, lon: -87.1, diameterKm: 32.7 },
  { name: 'Sverdrup', lat: -88.5, lon: -152.0, diameterKm: 33 },
  { name: 'Shoemaker', lat: -88.1, lon: 44.9, diameterKm: 51 },
  { name: 'Slater', lat: -88.1, lon: 110.5, diameterKm: 24 },
  { name: 'Haworth', lat: -87.45, lon: -5.0, diameterKm: 35 },
  { name: 'Faustini', lat: -87.3, lon: 77.0, diameterKm: 39 },
  { name: 'Cabeus', lat: -85.3, lon: -42.1, diameterKm: 98 },
  { name: 'Nobile', lat: -85.2, lon: 53.5, diameterKm: 73 },
  { name: 'Malapert', lat: -84.9, lon: 12.9, diameterKm: 69 },
  { name: 'Amundsen', lat: -84.4, lon: 85.6, diameterKm: 103 },
]
