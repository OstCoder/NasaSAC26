import * as React from 'react'
import { resolveFeatures, type FeatureFlags } from '@/config/features'
import { ApiError, api } from '@/services/api'
import type { AppConfig, LocationInput, Mode, Site } from '@/types/api'

/** A scenario the user is editing. Reused by the planner, comparison and rescheduler. */
export interface ScenarioDraft {
  location: LocationInput
  locationName: string
  landing_utc: string
  duration_hours: number
}

interface AppState {
  config: AppConfig
  sites: Site[]
  features: FeatureFlags
  mode: Mode
  setMode: (m: Mode) => void
  draftA: ScenarioDraft
  setDraftA: React.Dispatch<React.SetStateAction<ScenarioDraft>>
  draftB: ScenarioDraft
  setDraftB: React.Dispatch<React.SetStateAction<ScenarioDraft>>
}

const Ctx = React.createContext<AppState | null>(null)

export function useApp(): AppState {
  const v = React.useContext(Ctx)
  if (!v) throw new Error('useApp outside AppProvider')
  return v
}

export function siteDraftLocation(site: Site): Pick<ScenarioDraft, 'location' | 'locationName'> {
  return { location: { site_id: site.id }, locationName: site.name }
}

type Boot =
  | { state: 'loading' }
  | { state: 'error'; error: ApiError }
  | { state: 'ready'; config: AppConfig; sites: Site[] }

export function AppProvider({ children, fallback }: {
  children: React.ReactNode
  fallback: (boot: Exclude<Boot, { state: 'ready' }>, retry: () => void) => React.ReactNode
}) {
  const [boot, setBoot] = React.useState<Boot>({ state: 'loading' })
  const [attempt, setAttempt] = React.useState(0)

  React.useEffect(() => {
    let live = true
    setBoot({ state: 'loading' })
    Promise.all([api.config(), api.sites()])
      .then(([config, sites]) => live && setBoot({ state: 'ready', config, sites }))
      .catch((e: ApiError) => live && setBoot({ state: 'error', error: e }))
    return () => {
      live = false
    }
  }, [attempt])

  if (boot.state !== 'ready') return <>{fallback(boot, () => setAttempt((a) => a + 1))}</>
  return <ReadyProvider config={boot.config} sites={boot.sites}>{children}</ReadyProvider>
}

function ReadyProvider({ config, sites, children }: { config: AppConfig; sites: Site[]; children: React.ReactNode }) {
  const features = React.useMemo(() => resolveFeatures(config.features), [config.features])
  const [mode, setMode] = React.useState<Mode>(config.mode.default)
  const base = {
    landing_utc: config.simulation.default_landing_utc,
    duration_hours: config.simulation.default_duration_hours,
  }
  const [draftA, setDraftA] = React.useState<ScenarioDraft>({ ...base, ...siteDraftLocation(sites[0]) })
  // Default to the third mission candidate when the catalogue provides it.
  const [draftB, setDraftB] = React.useState<ScenarioDraft>({
    ...base,
    ...siteDraftLocation(sites[Math.min(2, sites.length - 1)]),
  })
  const value = { config, sites, features, mode, setMode, draftA, setDraftA, draftB, setDraftB }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
