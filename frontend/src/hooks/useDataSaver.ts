import * as React from 'react'

/**
 * "Data saver" preference: prefer the smaller imagery payloads and skip the
 * heavy 3D/global textures. Stored in localStorage so it persists across
 * sessions; auto-detected from the Network Information API on first visit.
 */
const KEY = 'lunanav.dataSaver'

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

function autoDetect(): boolean {
  const conn = (navigator as Navigator & { connection?: { effectiveType?: string } }).connection
  const et = conn?.effectiveType
  return et === 'slow-2g' || et === '2g' || et === '3g'
}

export function useDataSaver(): [boolean, (v: boolean) => void] {
  const [value, setValue] = React.useState<boolean>(() => {
    const stored = readStored()
    return stored !== null ? stored : autoDetect()
  })
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