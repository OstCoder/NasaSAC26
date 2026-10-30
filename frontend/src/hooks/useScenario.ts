import { api } from '@/services/api'
import type { Mode, ScenarioResult, Snapshot } from '@/types/api'
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
