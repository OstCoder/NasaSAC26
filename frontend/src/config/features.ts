/**
 * Feature flags. Server flags (config/lunanav.config.json -> GET /api/config)
 * are the default; a developer can override any flag locally without touching
 * the server, e.g. `?ff=experimental_power_model:on,rescheduler:off`.
 * Overrides from the URL are remembered in localStorage ("lunanav.ff").
 */
export type FeatureFlags = Record<string, boolean>

const STORAGE_KEY = 'lunanav.ff'

function readStored(): FeatureFlags {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as FeatureFlags
  } catch {
    return {}
  }
}

export function resolveFeatures(server: FeatureFlags, search = window.location.search): FeatureFlags {
  const overrides = { ...readStored() }
  const ff = new URLSearchParams(search).get('ff')
  if (ff) {
    for (const part of ff.split(',')) {
      const [k, v] = part.split(':')
      if (k) overrides[k.trim()] = v?.trim() !== 'off'
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides))
    } catch {
      /* storage unavailable: overrides apply to this load only */
    }
  }
  return { ...server, ...overrides }
}
