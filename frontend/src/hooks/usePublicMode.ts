import * as React from 'react'

/** "Public / educator" presentation mode: plain-language cards, larger text,
 * fewer decimals, and explicit "water ice: not assessed" framing. Same
 * calculations as planner mode; presentation only. Stored in localStorage so
 * it persists across sessions. */
const KEY = 'lunanav.publicMode'

function readStored(): boolean | null {
  try {
    const v = localStorage.getItem(KEY)
    if (v === '1') return true
    if (v === '0') return false
    return null
  } catch {
    return null
  }
}

export function usePublicMode(): [boolean, (v: boolean) => void] {
  const [value, setValue] = React.useState<boolean>(() => readStored() ?? false)
  const set = React.useCallback((v: boolean) => {
    try {
      localStorage.setItem(KEY, v ? '1' : '0')
    } catch {
      /* storage unavailable: preference applies to this load only */
    }
    setValue(v)
  }, [])
  return [value, set]
}
