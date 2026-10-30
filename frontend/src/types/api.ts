/**
 * Mirror of backend/app/models/schemas.py. Keep in sync when the API changes.
 * Datetimes arrive as ISO-8601 UTC strings.
 */

export type Mode = 'demo' | 'scientific'

export type ProvenanceLevel =
  | 'synthetic'
  | 'geometric_only'
  | 'analytic_approximate'
  | 'scientific_sourced'

export interface EffectsIncluded {
  terrain_topography: boolean
  optical_libration: boolean
  physical_libration: boolean
  observer_parallax: boolean
  light_time_correction: boolean
  finite_solar_disk: boolean
  lunar_curvature_in_horizon: boolean
  notes: string[]
}

export interface ProviderInfo {
  id: string
  kind: 'ephemeris' | 'terrain'
  name: string
  provenance: ProvenanceLevel
  source: string
  description: string
  effects: EffectsIncluded
  available: boolean
  unavailable_reason: string | null
  supported_start_utc: string | null
  supported_end_utc: string | null
}

export interface Provenance {
  mode: Mode
  overall: ProvenanceLevel
  label: string
  ephemeris: ProviderInfo
  terrain: ProviderInfo
  terrain_mask_source: string
  effects: EffectsIncluded
  caveats: string[]
}

export interface Site {
  id: string
  name: string
  latitude_deg: number
  longitude_deg: number
  region: string
  description: string
  coordinate_note: string
  tags: string[]
  source: string
}

export interface LocationInput {
  site_id?: string | null
  latitude_deg?: number | null
  longitude_deg?: number | null
  label?: string | null
  height_m?: number
}

export interface ResolvedLocation {
  site_id: string | null
  name: string
  latitude_deg: number
  longitude_deg: number
  is_custom: boolean
  height_m: number
}

export interface ScenarioInput {
  location: LocationInput
  landing_utc: string
  duration_hours: number
  step_minutes?: number | null
  mode?: Mode | null
  label?: string | null
}

export interface Interval {
  start_utc: string
  end_utc: string
  duration_hours: number
  clipped_start: boolean
  clipped_end: boolean
}

export interface IntervalSet {
  sun_visible: Interval[]
  earth_visible: Interval[]
  both_visible: Interval[]
  sun_blocked: Interval[]
  earth_blocked: Interval[]
  neither_visible: Interval[]
}

export interface TimeSeries {
  times_utc: string[]
  sun_azimuth_deg: number[]
  sun_elevation_deg: number[]
  sun_terrain_horizon_deg: number[]
  sun_disk_fraction: number[]
  sun_visible: boolean[]
  earth_azimuth_deg: number[]
  earth_elevation_deg: number[]
  earth_terrain_horizon_deg: number[]
  earth_visible: boolean[]
}

export type MetricCategory = 'sun' | 'earth' | 'combined' | 'geometry'

export interface MetricValue {
  id: string
  label: string
  value: number | null
  unit: string
  description: string
  category: MetricCategory
  censored: boolean
}

export interface HorizonMaskOut {
  azimuth_deg: number[]
  elevation_deg: number[]
  source: string
  provenance: ProvenanceLevel
}

export interface ScenarioResult {
  label: string | null
  location: ResolvedLocation
  landing_utc: string
  end_utc: string
  duration_hours: number
  step_minutes: number
  series: TimeSeries
  intervals: IntervalSet
  metrics: MetricValue[]
  horizon_mask: HorizonMaskOut
  provenance: Provenance
}

export interface BodyState {
  azimuth_deg: number
  elevation_deg: number
  terrain_horizon_deg: number
  clearance_deg: number
  visible: boolean
  disk_fraction: number | null
  next_transition_utc: string | null
  hours_until_transition: number | null
  transition_kind: 'set' | 'rise' | null
  transition_beyond_lookahead: boolean
}

export interface Snapshot {
  location: ResolvedLocation
  time_utc: string
  sun: BodyState
  earth: BodyState
  lookahead_hours: number
  provenance: Provenance
}

export interface MetricDelta {
  id: string
  label: string
  unit: string
  category: string
  a: number | null
  b: number | null
  delta: number | null
  percent_change: number | null
  either_censored: boolean
  availability_direction: -1 | 0 | 1
  statement: string
}

export interface ComparisonResult {
  a: ScenarioResult
  b: ScenarioResult
  deltas: MetricDelta[]
  tradeoffs: string[]
  comparable: boolean
  comparability_notes: string[]
}

export interface RescheduleResult {
  shift_hours: number
  comparison: ComparisonResult
  headline_changes: MetricDelta[]
}

export interface AppConfig {
  app: { name: string; version: string }
  mode: { default: Mode; allowed: Mode[] }
  simulation: {
    supported_start_utc: string
    supported_end_utc: string
    default_landing_utc: string
    default_duration_hours: number
    min_duration_hours: number
    max_duration_hours: number
    default_step_minutes: number
    min_step_minutes: number
    max_samples: number
    lookahead_hours_for_events: number
  }
  coordinates: Record<string, string | number>
  providers: Record<Mode, { ephemeris: string; terrain: string }>
  visibility: Record<string, string | number>
  features: Record<string, boolean>
}

export interface ApiErrorBody {
  code: string
  message: string
  details: Record<string, unknown>
}
