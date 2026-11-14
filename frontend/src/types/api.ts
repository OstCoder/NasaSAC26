/**
 * Mirror of backend/app/models/schemas.py. Keep in sync when the API changes.
 * Datetimes arrive as ISO-8601 UTC strings.
 */

export type Mode = 'demo' | 'jpl' | 'scientific'

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

export interface SourceRef {
  label: string
  url?: string | null
}

export interface PsrProximity {
  psr_id: string
  label: string
  distance_km: number
  area_km2: number
  centroid_latitude_deg: number
  centroid_longitude_deg: number
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
  /** Task 1 site-selection columns; null means not recorded, never zero. */
  nasa_site_id?: string | null
  elevation_m?: number | null
  elevation_note?: string | null
  slope_deg?: number | null
  nearest_psr?: PsrProximity | null
  psrs_within_10_km?: number | null
  sources?: SourceRef[]
}

export interface LocationInput {
  site_id?: string | null
  latitude_deg?: number | null
  longitude_deg?: number | null
  label?: string | null
  height_m?: number
  elevation_m?: number | null
}

export interface ResolvedLocation {
  site_id: string | null
  name: string
  latitude_deg: number
  longitude_deg: number
  is_custom: boolean
  height_m: number
  elevation_m?: number | null
}

export interface PsrOut {
  psr_id: string
  area_km2: number
  perimeter_km: number
  centroid_latitude_deg: number
  centroid_longitude_deg: number
  near_crater: string
  /** Rings in south polar stereographic km; draw with Leaflet [y, x]. */
  rings: number[][][]
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

export interface SubPoint {
  latitude_deg: number
  longitude_deg: number
  distance_km: number
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
  sub_point: SubPoint | null
}

export interface SkyNow {
  time_utc: string
  sun: SubPoint
  earth: SubPoint
  source: string
}

export interface Crater {
  name: string
  latitude_deg: number
  longitude_deg: number
  diameter_km: number
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

export interface LandingPreset {
  key: string
  label: string
  /** ISO-8601 UTC landing time. */
  utc: string
}

/** Phase 1 mission requirements, served from config → GET /api/config. */
export interface MissionRequirements {
  min_sun_visible_pct: number
  min_earth_visible_pct: number
  max_earth_blackout_hours: number
  psr_proximity: string
  basis: string
}

export type RequirementStatus = 'met' | 'not_met' | 'unknown'

export interface RequirementCheck {
  id: string
  label: string
  unit: string
  comparison: 'at_least' | 'at_most'
  threshold: number
  value: number | null
  status: RequirementStatus
  detail: string
}

export interface RequirementEvaluation {
  location: ResolvedLocation
  landing_utc: string
  duration_hours: number
  requirements_source: string
  checks: RequirementCheck[]
  satisfied: boolean | null
  nearest_psr?: PsrProximity | null
  psr_preference: string
  notes: string[]
}

export interface AppConfig {
  app: { name: string; version: string }
  mission: {
    name: string
    label: string
    profile: string
    objective: string
    duration_days: number
    landing_dates: { initial: string; alternative: string }
    spacecraft: { power: string; communication: string; crewed: boolean }
    candidate_sites: string[]
  }
  mode: { default: Mode; allowed: Mode[] }
  simulation: {
    supported_start_utc: string
    supported_end_utc: string
    default_landing_utc: string
    landing_presets: LandingPreset[]
    default_duration_hours: number
    min_duration_hours: number
    max_duration_hours: number
    default_step_minutes: number
    min_step_minutes: number
    max_samples: number
    lookahead_hours_for_events: number
  }
  /** Phase 1 Task 3 thresholds; mirrored in backend settings.RequirementThresholds. */
  requirements: MissionRequirements
  coordinates: Record<string, string | number>
  providers: Record<Mode, { ephemeris: string; terrain: string }>
  visibility: Record<string, string | number>
  features: Record<string, boolean>
  imagery: { default_layer: string; relief_layer: string; layers: Record<string, { label: string; credit: string; max_zoom: number }> }
}

export interface ServiceStatus {
  service: string
  url: string
  reachable: boolean
  message: string
  latency_ms: number
}

export interface JplStatus {
  checked_utc: string
  horizons: ServiceStatus
  trek: ServiceStatus
  horizons_cache: { directory: string; months: string[] } | null
}

export interface ApiErrorBody {
  code: string
  message: string
  details: Record<string, unknown>
}

/** Phase 2 Task 6: one body's angles in the on-disk record shape. */
export interface BodySample {
  azimuth_deg: number
  elevation_deg: number
  /** Observer-target range; omitted when Horizons did not return one. */
  range_km?: number
}

/** The Task 2 record, unchanged over HTTP: same fields as site_series/*.json. */
export interface SeriesRecord {
  site_id: string
  /** ISO-8601 UTC. */
  timestamp_utc: string
  sun: BodySample
  earth: BodySample
}

export interface MaskTier {
  dem: string
  pixel_m: number
  min_range_m: number
  max_range_m: number
  max_obstruction_deg: number
  max_obstruction_azimuth_deg: number
}

export interface SeriesMaskSummary {
  site_id: string
  source: string
  azimuth_step_deg: number
  max_range_km: number
  max_obstruction_deg: number
  max_obstruction_azimuth_deg: number
  observer_height_m: number
  dem: string
  /** Near (5 m) and far (80 m) tiers; null only for older single-tier masks. */
  tiers?: { near: MaskTier; far: MaskTier | null } | null
  available: true
}

/** GET /api/series. Geometry only: clearance is not a visibility verdict. */
export interface SiteSeries {
  schema: 'lunanav.series_access.v1'
  records_schema: 'lunanav.site_series.v1'
  site: {
    site_id: string
    name: string
    latitude_deg: number
    longitude_deg: number
    elevation_m: number
    height_m: number
    altitude_km: number
  }
  window: { key: string; label: string; start_utc: string; stop_utc: string }
  request: {
    start_utc: string
    stop_utc: string
    step_minutes: number
    native_step: string
    interpolated: boolean
    samples: number
  }
  mask: SeriesMaskSummary | null
  provenance: Record<string, string>
  fields: string[]
  checks: Record<string, boolean>
  series: SeriesRecord[]
}

export interface SiteReadiness {
  site_id: string
  name: string
  latitude_deg: number
  longitude_deg: number
  elevation_m: number | null
  windows: Record<string, { start_utc: string; stop_utc: string; records: number; step: string }>
  mask: SeriesMaskSummary | null
  ready: boolean
  problems: string[]
}

export interface Phase3WindowSummary {
  available: boolean
  reason?: string
  samples?: number
  mask_max_range_km?: number
  summary?: {
    sun_visible_pct: number
    sun_visible_hours: number
    longest_sun_blackout_hours: number | null
    earth_visible_pct: number
    earth_visible_hours: number
    longest_earth_blackout_hours: number | null
    both_visible_pct: number
    both_visible_hours: number
    longest_no_simultaneous_hours: number | null
  }
}

/** GET /api/phase3/windows: both mission windows per candidate, offline. */
export interface Phase3Windows {
  schema: 'lunanav.phase3_windows.v1'
  step: string
  sites: { site_id: string; windows: Record<string, Phase3WindowSummary> }[]
  notes: string[]
}

/** GET /api/readiness: what Phase 3 needs, per mission candidate. */
export interface ReadinessReport {
  schema: 'lunanav.phase3_readiness.v1'
  generated_utc: string
  sites: SiteReadiness[]
  summary: { sites: number; ready: number; with_mask: number; missing: string[] }
  notes: string[]
}
