/**
 * Typed client for the LunaNav API. Components never call fetch directly,
 * so the transport (proxy, deployed host, mock) can change in one place.
 */
import type {
  ApiErrorBody,
  AppConfig,
  ComparisonResult,
  JplStatus,
  LocationInput,
  Mode,
  ProviderInfo,
  RescheduleResult,
  ScenarioInput,
  ScenarioResult,
  Site,
  Snapshot,
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
  scenario: (input: ScenarioInput, signal?: AbortSignal) => post<ScenarioResult>('/api/scenario', input, signal),
  snapshot: (
    body: { location: LocationInput; time_utc: string; mode?: Mode; lookahead_hours?: number },
    signal?: AbortSignal,
  ) => post<Snapshot>('/api/snapshot', body, signal),
  jplStatus: (force = false) => request<JplStatus>(`/api/jpl/status${force ? '?force=true' : ''}`),
  /** URLs for image endpoints (used directly by <img>/Leaflet/three.js loaders). */
  southPoleImageryUrl: (layer: string, size = 2048, maxLat = -80) =>
    `${BASE}/api/imagery/south-pole?layer=${encodeURIComponent(layer)}&size=${size}&max_lat=${maxLat}`,
  globalImageryUrl: (layer = 'wac', zoom = 2) =>
    `${BASE}/api/imagery/global?layer=${encodeURIComponent(layer)}&zoom=${zoom}`,
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
  reschedule: (body: {
    location: LocationInput
    original_landing_utc: string
    proposed_landing_utc: string
    duration_hours: number
    mode?: Mode
  }) => post<RescheduleResult>('/api/reschedule', body),
}
