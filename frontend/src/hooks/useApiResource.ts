import * as React from 'react'
import { ApiError } from '@/services/api'

export interface Resource<T> {
  data: T | null
  error: ApiError | null
  loading: boolean
}

/**
 * Runs `fetcher` whenever `key` changes (debounced), aborting stale requests.
 * Keeps the previous data while loading so charts don't flash empty.
 */
export function useApiResource<T>(
  key: string | null,
  fetcher: (signal: AbortSignal) => Promise<T>,
  debounceMs = 250,
): Resource<T> {
  const [state, setState] = React.useState<Resource<T>>({ data: null, error: null, loading: false })
  const fetchRef = React.useRef(fetcher)
  fetchRef.current = fetcher

  React.useEffect(() => {
    if (key === null) return
    const ctrl = new AbortController()
    setState((s) => ({ ...s, loading: true }))
    const timer = window.setTimeout(() => {
      fetchRef.current(ctrl.signal)
        .then((data) => setState({ data, error: null, loading: false }))
        .catch((e: unknown) => {
          if (ctrl.signal.aborted) return
          const err = e instanceof ApiError ? e : new ApiError(0, { code: 'UNKNOWN', message: String(e), details: {} })
          setState({ data: null, error: err, loading: false })
        })
    }, debounceMs)
    return () => {
      ctrl.abort()
      window.clearTimeout(timer)
    }
  }, [key, debounceMs])

  return state
}
