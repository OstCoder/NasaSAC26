import * as React from 'react'
import { api } from '@/services/api'
import type {
  Crater,
  EngineeringBudget,
  FeasibilityMatrix,
  Mode,
  Phase3Windows,
  ReadinessReport,
  ScenarioResult,
  SiteSeries,
  SkyNow,
  Snapshot,
  TerrainDem,
  TerrainHorizon,
} from '@/types/api'
import type { ScenarioDraft } from './useAppContext'
import { useApiResource } from './useApiResource'

export function draftToInput(d: ScenarioDraft, mode: Mode, label?: string) {
  return { location: d.location, landing_utc: d.landing_utc, duration_hours: d.duration_hours, mode, label }
}

export function useScenario(draft: ScenarioDraft, mode: Mode) {
  const input = draftToInput(draft, mode)
  return useApiResource<ScenarioResult>(JSON.stringify(input), (signal) => api.scenario(input, signal))
}

export function useSnapshot(draft: ScenarioDraft, timeUtc: string | null, mode: Mode) {
  const body = timeUtc ? { location: draft.location, time_utc: timeUtc, mode } : null
  return useApiResource<Snapshot>(body ? JSON.stringify(body) : null, (signal) => api.snapshot(body!, signal), 200)
}

const SKY_REFRESH_MS = 60_000

/** Sun and Earth positions right now, refreshed each minute (the Sun moves ~0.5°/hour across the Moon). */
export function useSkyNow(mode: Mode) {
  const [tick, setTick] = React.useState(0)
  React.useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), SKY_REFRESH_MS)
    return () => window.clearInterval(id)
  }, [])
  return useApiResource<SkyNow>(`${mode}:${tick}`, (signal) => api.skyNow(mode, signal), 0)
}

export function useReadiness() {
  return useApiResource<ReadinessReport>('readiness', (signal) => api.readiness(signal), 0)
}

/** Phase 3 visibility for every candidate and window, computed from the committed data. */
export function usePhase3Windows() {
  return useApiResource<Phase3Windows>('phase3-windows', (signal) => api.phase3Windows(signal), 0)
}

/** Phase 4 Task 1: one site's terrain horizon profile, with Sun/Earth compared against it. */
export function useSiteHorizon(siteId: string, window: string, enabled = true) {
  return useApiResource<TerrainHorizon>(
    enabled ? `terrain-horizon:${siteId}:${window}` : null,
    (signal) => api.terrainHorizon({ siteId, window }, signal),
    0,
  )
}

/** The committed Sun/Earth track for the same site and window, for the overlaid points. */
export function useSiteSeries(siteId: string, window: string, enabled = true) {
  return useApiResource<SiteSeries>(
    enabled ? `series:${siteId}:${window}` : null,
    (signal) => api.series({ siteId, window }, signal),
    0,
  )
}

/** Phase 4: the feasibility matrix — every candidate x both windows vs the requirements. */
export function useFeasibilityMatrix() {
  return useApiResource<FeasibilityMatrix>('feasibility-matrix', (signal) => api.feasibilityMatrix(signal), 0)
}

/** Phase 4 Task 6 (experimental): one candidate's pooled LOLA DEM grid, display only. */
export function useSiteDem(siteId: string, enabled = true) {
  return useApiResource<TerrainDem>(
    enabled ? `site-dem:${siteId}` : null,
    (signal) => api.terrainDem({ siteId }, signal),
    0,
  )
}

export function useCraters() {
  return useApiResource<Crater[]>('craters', (signal) => api.craters(signal), 0)
}

/** Phase 5: the power and link budgets for one candidate and window. */
export function useSiteEngineering(siteId: string, window: string) {
  return useApiResource<EngineeringBudget>(
    `engineering:${siteId}:${window}`,
    (signal) => api.engineering({ siteId, window }, signal),
    0,
  )
}
