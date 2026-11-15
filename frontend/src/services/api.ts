/**
 * Typed client for the LunaNav API. Components never call fetch directly,
 * so the transport (proxy, deployed host, mock) can change in one place.
 */
import type {
  Crater,
  SkyNow,
  ApiErrorBody,
  AppConfig,
  ComparisonResult,
  DecisionRequest,
  DecisionResult,
  FeasibilityMatrix,
  JplStatus,
  LocationInput,
  Mode,
  ProviderInfo,
  Phase3Windows,
  PsrOut,
  ReadinessReport,
  RequirementEvaluation,
  RequirementThresholdsInput,
  EngineeringBudget,
  RescheduleResult,
  ScenarioInput,
  ScenarioResult,
  Site,
  SiteSeries,
  Snapshot,
  ScienceNearestPsr,
  SciencePsrCatalogue,
  ScienceSiteContext,
  TerrainDem,
  TerrainHorizon,
} from '@/types/api'

const BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>
  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.code = body.code
    this.status = status
    this.details = body.details ?? {}
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, {
      code: 'BACKEND_UNREACHABLE',
      message: 'Cannot reach the LunaNav backend. Start it with: cd backend && uvicorn app.main:app --port 8000',
      details: {},
    })
  }
  if (!res.ok) {
    let body: ApiErrorBody
    try {
      body = (await res.json()) as ApiErrorBody
    } catch {
      body = { code: 'HTTP_' + res.status, message: res.statusText, details: {} }
    }
    throw new ApiError(res.status, body)
  }
  return (await res.json()) as T
}

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body), signal })

export const api = {
  config: () => request<AppConfig>('/api/config'),
  providers: (mode: Mode) => request<ProviderInfo[]>(`/api/providers?mode=${mode}`),
  sites: () => request<Site[]>('/api/sites'),
  /** Phase 2 Task 6: committed Sun/Earth track, optionally resampled (never extrapolated). */
  series: (
    opts: { siteId: string; window?: string; start?: string; stop?: string; stepMinutes?: number },
    signal?: AbortSignal,
  ) => {
    const q = new URLSearchParams({ site_id: opts.siteId })
    if (opts.window) q.set('window', opts.window)
    if (opts.start) q.set('start', opts.start)
    if (opts.stop) q.set('stop', opts.stop)
    if (opts.stepMinutes !== undefined) q.set('step_minutes', String(opts.stepMinutes))
    return request<SiteSeries>(`/api/series?${q.toString()}`, { signal })
  },
  /** Which candidates have both mission windows and a LOLA skyline. */
  readiness: (signal?: AbortSignal) => request<ReadinessReport>('/api/readiness', { signal }),
  /** Phase 3: terrain-adjusted visibility, both windows, from committed data (offline). */
  phase3Windows: (signal?: AbortSignal) =>
    request<Phase3Windows>('/api/phase3/windows', { signal }),
  /** Phase 4 Task 6 (experimental): one candidate's pooled LOLA DEM grid (display only). */
  terrainDem: (opts: { siteId: string }, signal?: AbortSignal) =>
    request<TerrainDem>(`/api/terrain-dem?site_id=${encodeURIComponent(opts.siteId)}`, { signal }),
  /** Phase 3 Task 3 / Phase 4: the horizon profile and Sun/Earth against it (offline). */
  terrainHorizon: (
    opts: { siteId?: string; latitudeDeg?: number; longitudeDeg?: number; window?: string },
    signal?: AbortSignal,
  ) => {
    const q = new URLSearchParams()
    if (opts.siteId) q.set('site_id', opts.siteId)
    if (opts.latitudeDeg !== undefined) q.set('latitude_deg', String(opts.latitudeDeg))
    if (opts.longitudeDeg !== undefined) q.set('longitude_deg', String(opts.longitudeDeg))
    if (opts.window) q.set('window', opts.window)
    return request<TerrainHorizon>(`/api/terrain-horizon?${q.toString()}`, { signal })
  },
  /** Phase 5: solar-power and link budgets from the committed track (offline). */
  engineering: (
    opts: {
      siteId: string
      window?: string
      loadW?: number
      panelDesign?: 'horizontal' | 'vertical_tracking' | 'fixed'
      panelTiltDeg?: number
      panelAzimuthDeg?: number
    },
    signal?: AbortSignal,
  ) => {
    const q = new URLSearchParams({ site_id: opts.siteId })
    if (opts.window) q.set('window', opts.window)
    if (opts.loadW !== undefined) q.set('load_w', String(opts.loadW))
    if (opts.panelDesign) q.set('panel_design', opts.panelDesign)
    if (opts.panelTiltDeg !== undefined) q.set('panel_tilt_deg', String(opts.panelTiltDeg))
    if (opts.panelAzimuthDeg !== undefined) q.set('panel_azimuth_deg', String(opts.panelAzimuthDeg))
    return request<EngineeringBudget>(`/api/engineering?${q.toString()}`, { signal })
  },
  /** Phase 5: evaluate and transparently rank every mission candidate. */
  decision: (body: DecisionRequest, signal?: AbortSignal) =>
    post<DecisionResult>('/api/decision', body, signal),
  /** Phase 5 Task 3: the deterministic Markdown mission report, for download. */
  missionReportUrl: (opts: { siteId: string; window?: string }) => {
    const q = new URLSearchParams({ site_id: opts.siteId })
    if (opts.window) q.set('window', opts.window)
    return `${BASE}/api/mission-report.md?${q.toString()}`
  },
  scenario: (input: ScenarioInput, signal?: AbortSignal) => post<ScenarioResult>('/api/scenario', input, signal),
  /** Check one scenario against optional user-adjusted thresholds (defaults from /api/config). */
  requirements: (input: ScenarioInput, thresholds?: RequirementThresholdsInput, signal?: AbortSignal) =>
    post<RequirementEvaluation>('/api/requirements', thresholds ? { ...input, thresholds } : input, signal),
  snapshot: (
    body: { location: LocationInput; time_utc: string; mode?: Mode; lookahead_hours?: number },
    signal?: AbortSignal,
  ) => post<Snapshot>('/api/snapshot', body, signal),
  craters: (signal?: AbortSignal) => request<Crater[]>('/api/craters', { signal }),
  /** Phase 6: verified PSR catalogue with source metadata. */
  sciencePsrs: (opts?: { minAreaKm2?: number; maxLat?: number; nearSiteId?: string; radiusKm?: number }, signal?: AbortSignal) => {
    const q = new URLSearchParams()
    if (opts?.minAreaKm2 !== undefined) q.set('min_area_km2', String(opts.minAreaKm2))
    if (opts?.maxLat !== undefined) q.set('max_latitude_deg', String(opts.maxLat))
    if (opts?.nearSiteId) q.set('near_site_id', opts.nearSiteId)
    if (opts?.radiusKm !== undefined) q.set('radius_km', String(opts.radiusKm))
    const qs = q.toString()
    return request<SciencePsrCatalogue>(`/api/science/psrs${qs ? `?${qs}` : ''}`, { signal })
  },
  /** Phase 6: nearest mapped PSR and nearby mapped regions. */
  scienceNearestPsr: (
    opts: { siteId?: string; latitudeDeg?: number; longitudeDeg?: number; radiusKm?: number; limit?: number },
    signal?: AbortSignal,
  ) => {
    const q = new URLSearchParams()
    if (opts.siteId) q.set('site_id', opts.siteId)
    if (opts.latitudeDeg !== undefined) q.set('latitude_deg', String(opts.latitudeDeg))
    if (opts.longitudeDeg !== undefined) q.set('longitude_deg', String(opts.longitudeDeg))
    if (opts.radiusKm !== undefined) q.set('radius_km', String(opts.radiusKm))
    if (opts.limit !== undefined) q.set('limit', String(opts.limit))
    return request<ScienceNearestPsr>(`/api/science/nearest-psr?${q.toString()}`, { signal })
  },
  /** Phase 6: PSR, terrain and visibility context for one candidate. */
  scienceSiteContext: (siteId: string, signal?: AbortSignal) =>
    request<ScienceSiteContext>(`/api/science/site-context?site_id=${encodeURIComponent(siteId)}`, { signal }),
  /** PSR polygons (LROC/LOLA); rings in south polar stereographic km. */
  psrs: (opts?: { minAreaKm2?: number; maxLat?: number; nearSiteId?: string; radiusKm?: number }, signal?: AbortSignal) => {
    const q = new URLSearchParams()
    if (opts?.minAreaKm2 !== undefined) q.set('min_area_km2', String(opts.minAreaKm2))
    if (opts?.maxLat !== undefined) q.set('max_latitude_deg', String(opts.maxLat))
    if (opts?.nearSiteId) q.set('near_site_id', opts.nearSiteId)
    if (opts?.radiusKm !== undefined) q.set('radius_km', String(opts.radiusKm))
    const qs = q.toString()
    return request<PsrOut[]>(`/api/psrs${qs ? `?${qs}` : ''}`, { signal })
  },
  skyNow: (mode: Mode, signal?: AbortSignal) => request<SkyNow>(`/api/sky/now?mode=${mode}`, { signal }),
  jplStatus: (force = false) => request<JplStatus>(`/api/jpl/status${force ? '?force=true' : ''}`),
  /** URLs for image endpoints (used directly by <img>/Leaflet/three.js loaders). */
  southPoleImageryUrl: (layer: string, size = 2048, maxLat = -80) =>
    `${BASE}/api/imagery/south-pole?layer=${encodeURIComponent(layer)}&size=${size}&max_lat=${maxLat}`,
  globalImageryUrl: (layer = 'wac', zoom = 2) =>
    `${BASE}/api/imagery/global?layer=${encodeURIComponent(layer)}&zoom=${zoom}`,
  reliefUrl: (kind: 'height' | 'normal', zoom: number) => `${BASE}/api/imagery/relief?kind=${kind}&zoom=${zoom}`,
  /** Leaflet tile template: Moon Trek's {row}/{col} are Leaflet's {y}/{x}. */
  tileUrlTemplate: (layer: string) => `${BASE}/api/imagery/tile/${encodeURIComponent(layer)}/{z}/{y}/{x}`,
  /** Fetch an image endpoint only to read its JSON error, after the image failed to load. */
  imageryError: async (url: string): Promise<ApiError | null> => {
    try {
      await request<unknown>(url.replace(BASE, ''))
      return null
    } catch (e) {
      return e instanceof ApiError ? e : null
    }
  },
  compare: (a: ScenarioInput, b: ScenarioInput) => post<ComparisonResult>('/api/compare', { a, b }),
  /** Phase 4: every candidate x both windows against the Phase 1 requirements (offline). */
  feasibilityMatrix: (signal?: AbortSignal) => request<FeasibilityMatrix>('/api/feasibility', { signal }),
  reschedule: (body: {
    location: LocationInput
    original_landing_utc: string
    proposed_landing_utc: string
    duration_hours: number
    mode?: Mode
  }) => post<RescheduleResult>('/api/reschedule', body),
}
