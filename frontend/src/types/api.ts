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

/** Phase 6 science context. Distance is geometry, never a traverse or ice detection. */
export interface SciencePsrEntry {
  psr_id: string
  label: string
  near_crater: string | null
  area_km2: number
  perimeter_km: number
  boundary_distance_km: number
  centroid_distance_km: number
  inside: boolean
  distance_uncertainty_km: number
  centroid_latitude_deg: number
  centroid_longitude_deg: number
}

export interface SciencePsrCatalogue {
  schema: 'lunanav.science_psr_catalogue.v1'
  count: number
  catalogue_count: number
  area_threshold_km2: number
  max_latitude_deg: number
  projection: Record<string, unknown> | null
  source: Record<string, unknown> | null
  psrs: (PsrOut & { boundary_distance_km?: number })[]
  limits: string[]
}

export interface ScienceNearestPsr {
  schema: 'lunanav.science_context.v1'
  query: {
    site_id: string | null
    name: string
    latitude_deg: number
    longitude_deg: number
    radius_km: number
  }
  nearest_psr: SciencePsrEntry
  nearby_psrs: SciencePsrEntry[]
  nearby_count: number
  status: 'inside' | 'mapped'
  water_ice: {
    confirmed: null
    status: 'not_assessed'
    evidence: string[]
    interpretation: string
  }
  distance_basis: string
  source: Record<string, unknown>
  limits: string[]
  notes: string[]
}

export interface ScienceSiteContext {
  schema: 'lunanav.science_context.v1'
  site: {
    site_id: string | null
    name: string
    latitude_deg: number
    longitude_deg: number
    elevation_m: number | null
    slope_deg: number | null
    region: string
    description: string
    sources: SourceRef[]
  }
  nearest_psr: SciencePsrEntry
  nearby_psrs: SciencePsrEntry[]
  nearby_count: number
  terrain: {
    available: boolean
    basis: 'terrain' | 'geometric'
    geometric_only: boolean
    source: string
    provenance: string
    surface_elevation_m?: number | null
    observer_height_m: number
    coverage: TerrainCoverage
    uncertainty: TerrainUncertainty
    limits: string[]
  }
  visibility_windows: Record<string, {
    available: boolean
    label?: string
    start_utc?: string
    stop_utc?: string
    sun_visible_pct?: number | null
    earth_visible_pct?: number | null
    longest_sun_blackout_hours?: number | null
    longest_earth_blackout_hours?: number | null
    reason?: string
  }>
  science: {
    water_ice_confirmed: null
    water_ice_status: 'not_assessed'
    water_ice_evidence: string[]
    psr_interpretation: string
    temperature: null
    temperature_note: string
  }
  status: 'calculated' | 'partial'
  provenance: Record<string, string | null>
  limits: string[]
  notes: string[]
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

export interface DelayPowerComparison {
  available: boolean
  original: DecisionPower
  proposed: DecisionPower
  deltas: Record<string, number | null>
  summary: string
  notes: string[]
}

export interface DelayRequirementComparison {
  original: RequirementEvaluation
  proposed: RequirementEvaluation
  new_failures: string[]
  improvements: string[]
  summary: string
}

export interface RescheduleResult {
  shift_hours: number
  comparison: ComparisonResult
  headline_changes: MetricDelta[]
  power?: DelayPowerComparison | null
  requirements?: DelayRequirementComparison | null
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
  max_darkness_hours: number
  power_demand_w: number
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
  /** False when the caller made this check advisory; it is shown but does not gate ranking. */
  required?: boolean
  detail: string
}

export interface RequirementThresholdsInput {
  min_sun_visible_pct?: number
  min_earth_visible_pct?: number
  max_earth_blackout_hours?: number
  max_darkness_hours?: number
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
    sun_only_hours: number
    earth_only_hours: number
    sun_blocked_hours: number
    longest_sun_visible_hours: number
    longest_earth_visible_hours: number
  }
}

/** GET /api/phase3/windows: both mission windows per candidate, offline. */
export interface Phase3Windows {
  schema: 'lunanav.phase3_windows.v1'
  step: string
  sites: { site_id: string; windows: Record<string, Phase3WindowSummary> }[]
  notes: string[]
}

export interface TerrainProfile {
  /** 0…359, clockwise from local north, strictly increasing. */
  azimuth_deg: number[]
  elevation_deg: number[]
}

export interface TerrainTier {
  pixel_m: number | null
  max_range_m: number | null
  dem: string | null
}

export interface TerrainCoverage {
  near: TerrainTier
  far: TerrainTier
  max_sampled_range_km: number | null
  azimuth_step_deg: number
  curvature_applied: boolean
  curvature_radius_m: number
  curvature_model: string
  beyond_range_note: string
}

export interface TerrainUncertainty {
  observer_height_m: number
  observer_height_uncertainty_m: number | null
  near_pixel_m: number | null
  far_pixel_m: number | null
  azimuth_step_deg: number
  max_range_km: number | null
  unmodelled: string[]
}

export interface TerrainHorizonSummary {
  max_obstruction_deg: number
  min_obstruction_deg: number
  mean_obstruction_deg: number
  max_obstruction_azimuth_deg: number | null
}

/** One body's samples compared with the skyline at their own azimuths. */
export interface TerrainBodyComparison {
  samples: number
  above_skyline: number
  below_skyline: number
  above_skyline_pct: number
  max_clearance_deg: number
  min_clearance_deg: number
  skyline_min_deg: number
  skyline_max_deg: number
  elevation_max_deg: number
  elevation_min_deg: number
  flat_horizon_visible: number
  blocked_by_terrain: number
  visible_added_by_terrain: number
  agrees_with_visibility: boolean
  rule: string
}

/** GET /api/terrain-horizon: profile, coverage and Sun/Earth against the skyline. */
export interface TerrainHorizon {
  schema: 'lunanav.terrain_horizon.v1'
  site: {
    site_id: string | null
    name: string | null
    latitude_deg: number | null
    longitude_deg: number | null
    elevation_m: number | null
  }
  window: { key: string; label?: string; start_utc?: string; stop_utc?: string; step?: string; samples?: number }
  terrain: {
    available: boolean
    basis: 'terrain' | 'geometric'
    geometric_only: boolean
    source: string
    provenance: string
    observer_height_m: number
    azimuth_step_deg: number
    surface_elevation_m: number | null
    profile: TerrainProfile
    summary: TerrainHorizonSummary
    coverage: TerrainCoverage
    uncertainty: TerrainUncertainty
    limits: string[]
  }
  comparison: { sun: TerrainBodyComparison | null; earth: TerrainBodyComparison | null }
  visibility: {
    available: boolean
    basis: 'terrain' | 'geometric'
    geometric_only: boolean
    window: { key: string }
    reason?: string
    summary: NonNullable<Phase3WindowSummary['summary']> | null
    series_endpoint: string | null
  }
  checks: Record<string, boolean>
  provenance: Record<string, string | number | null>
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

/** Phase 4: the feasibility matrix — GET /api/feasibility. */
export interface FeasibilityGeometricBaseline {
  basis: 'geometric'
  horizon_rule: string
  sun: { visible_sample_pct: number; grazing_samples: number }
  earth: { visible_sample_pct: number; grazing_samples: number }
  notes: string[]
}

export interface FeasibilityRow {
  site_id: string
  name?: string
  latitude_deg?: number | null
  longitude_deg?: number | null
  window: { key: string; label?: string; start_utc?: string; stop_utc?: string; samples?: number }
  available?: boolean
  reason?: string
  basis?: 'terrain' | null
  mask?: { provenance: string; source: string | null; max_range_km: number | null }
  summary?: {
    sun_visible_pct: number | null
    earth_visible_pct: number | null
    both_visible_pct: number | null
    longest_sun_blackout_hours: number | null
    longest_earth_blackout_hours: number | null
    longest_no_simultaneous_hours: number | null
  }
  checks: RequirementCheck[]
  satisfied: boolean | null
  geometric_baseline?: FeasibilityGeometricBaseline
  context?: { nearest_psr: PsrProximity | null; psrs_within_10_km: number | null }
}

export interface FeasibilityThresholds {
  min_sun_visible_pct: number
  min_earth_visible_pct: number
  max_earth_blackout_hours: number
  max_darkness_hours: number
}

export interface FeasibilityMatrix {
  schema: 'lunanav.feasibility_matrix.v1'
  requirements_source: string
  thresholds: FeasibilityThresholds
  rows: FeasibilityRow[]
  notes: string[]
}

/** Phase 4 Task 6 (experimental): pooled site DEM grid — GET /api/terrain-dem. */
export interface TerrainDem {
  schema: 'lunanav.terrain_dem.v1'
  site: { site_id: string; name: string; latitude_deg: number; longitude_deg: number }
  grid: {
    size: number
    cell_m: number
    extent_m: { east_west: number; north_south: number }
    bounds_m: { left: number; bottom: number; right: number; top: number }
    site_cell: { col: number; row: number }
    nodata_fill_cells: number
  }
  heights_m: number[][]
  site_height_m: number
  height_convention: string
  crs: string
  source: { label: string; provider: string; file: string; sha256: string; citation: string }
  provenance: string
  notes: string[]
}

export interface PowerSeries {
  times_utc: string[]
  solar_w: number[]
  load_w: number[]
  battery_wh: number[]
  battery_soc_pct: number[]
  sun_visible: boolean[]
  charging: boolean[]
  discharging: boolean[]
  unserved_wh: number[]
}

export interface PowerExtremes {
  min_battery_wh: number
  min_battery_soc_pct: number
  min_battery_index: number
  shortage_samples: number
  shortage_hours: number
}

/** Phase 5 Task 1-2: solar-power and direct-to-Earth budgets — GET /api/engineering. */
export interface LinkCase {
  range_km: number
  fspl_db: number
  cn0_db_hz: number
  supported_rate_bps: number
  margin_db: number
}

export interface PowerDesign {
  id: 'horizontal' | 'vertical_tracking' | 'fixed'
  label: string
  incidence_rule: string
  tilt_deg: number
  azimuth_deg: number | null
  tracking: boolean
  peak_w: number
  mean_w: number
  energy_wh: number
  capacity_factor_pct: number
}

export interface PowerSensitivityCase {
  id: string
  label: string
  parameter: string
  factor: number
  load_w: number
  array_energy_wh: number
  min_soc_pct: number
  unserved_wh: number
  reserve_respected: boolean
}

export interface PowerSensitivity {
  method: string
  design: string
  base_energy_wh: number
  cases: PowerSensitivityCase[]
  min_soc_range_pct: [number, number]
  max_unserved_wh: number
  limits: string[]
}

export interface EngineeringBudget {
  schema: 'lunanav.engineering_budget.v1'
  site: {
    site_id: string
    name: string | null
    latitude_deg: number | null
    longitude_deg: number | null
    elevation_m: number | null
  }
  window: { key: string; label?: string; start_utc?: string; stop_utc?: string; step?: string; samples?: number }
  power: {
    assumptions: {
      solar_constant_w_m2: number
      panel_area_m2: number
      cell_efficiency: number
      packing_factor: number
      harness_and_soiling_factor: number
      load_w: number
      battery_capacity_wh: number
      battery_max_depth_of_discharge: number
      initial_state_of_charge: number
      default_panel_design: string
      default_panel_tilt_deg: number
      default_panel_azimuth_deg: number
      basis: string
      derived: { dc_w_per_m2_at_normal_incidence: number; conversion_factor: number; irradiance_au: number }
    }
    design: {
      recommended: string
      selected: 'horizontal' | 'vertical_tracking' | 'fixed'
      tilt_deg: number
      azimuth_deg: number | null
      tracking: boolean
      reason: string
    }
    designs: PowerDesign[]
    sensitivity: PowerSensitivity
    window: { hours: number; sunlit_hours: number; dark_hours: number; sunlit_pct: number }
    budget: {
      load_w: number
      load_wh: number
      array_energy_wh: number
      net_wh: number
      battery: DecisionBattery
    }
    series: PowerSeries
    extremes: PowerExtremes
    limits: string[]
  }
  link: {
    assumptions: {
      frequency_ghz: number
      transmit_power_w: number
      transmit_antenna_gain_dbi: number
      receive_dish_diameter_m: number
      receive_aperture_efficiency: number
      system_noise_temperature_k: number
      implementation_loss_db: number
      required_ebno_db: number
      modulation: string
      basis: string
      derived: {
        wavelength_m: number
        eirp_dbw: number
        receive_gain_dbi: number
        g_over_t_db_k: number
      }
    }
    window: { hours: number; visible_hours: number; data_volume_bound_mb: number; outage_hours: number }
    best_case: LinkCase | null
    worst_case: LinkCase | null
    closes: boolean
    verdict: string
    limits: string[]
  }
  provenance: Record<string, string>
  notes: string[]
}

/** Phase 5 Tasks 1-12: one decision-support evaluation and ranking — POST /api/decision. */
export interface DecisionThresholdsInput extends RequirementThresholdsInput {
  power_demand_w?: number
}

export interface DecisionWeights {
  sunlight: number
  earth_visibility: number
  communication: number
  science: number
}

export interface DecisionRequest {
  landing_utc: string
  duration_hours: number
  mode?: Mode | null
  site_ids?: string[]
  custom_location?: LocationInput
  thresholds?: DecisionThresholdsInput
  weights?: Partial<DecisionWeights>
  panel_design?: 'horizontal' | 'vertical_tracking' | 'fixed'
  panel_tilt_deg?: number
  panel_azimuth_deg?: number
  optional_checks?: string[]
}

export interface DecisionBattery {
  capacity_wh: number
  usable_wh: number
  initial_soc_pct: number
  min_soc_pct: number
  final_soc_pct: number
  unserved_wh: number
  depleted: boolean
  reserve_pct: number
  reserve_respected: boolean
  verdict: string
}

export interface DecisionPower {
  available: boolean
  window: 'initial' | 'alternative' | null
  load_w: number | null
  load_wh: number | null
  array_energy_wh: number | null
  net_wh: number | null
  battery: DecisionBattery | null
  panel_design?: string | null
  panel_tilt_deg?: number | null
  panel_azimuth_deg?: number | null
  reason: string | null
}

export interface DecisionSite {
  site_id: string
  name: string
  latitude_deg: number
  longitude_deg: number
  status: 'pass' | 'fail' | 'unknown'
  satisfied: boolean | null
  checks: RequirementCheck[]
  metrics: Record<string, number | null>
  rank: number | null
  score: number | null
  score_components: Record<string, number>
  power: DecisionPower
  nearest_psr: PsrProximity | null
  psrs_within_10_km: number | null
  reasons: string[]
  risks: string[]
  provenance: string
}

export interface DecisionResult {
  schema: 'lunanav.mission_decision.v1'
  landing_utc: string
  duration_hours: number
  mode: Mode
  thresholds: {
    min_sun_visible_pct: number
    min_earth_visible_pct: number
    max_earth_blackout_hours: number
    max_darkness_hours: number
    power_demand_w: number
  }
  weights: DecisionWeights
  recommendation: {
    status: 'ranked' | 'no_eligible_site'
    top_site_id: string | null
    top_site_name: string | null
    ranked_site_ids: string[]
    summary: string
  }
  sites: DecisionSite[]
  notes: string[]
}
