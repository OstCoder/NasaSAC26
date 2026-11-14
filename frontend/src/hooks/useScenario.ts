import * as React from 'react'
import { api } from '@/services/api'
import type { Crater, Mode, Phase3Windows, ReadinessReport, ScenarioResult, SkyNow, Snapshot } from '@/types/api'
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

export function useCraters() {
  return useApiResource<Crater[]>('craters', (signal) => api.craters(signal), 0)
}
