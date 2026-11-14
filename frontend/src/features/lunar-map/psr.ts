/**
 * Permanently shadowed regions (LROC/LOLA south-polar product, PSRs > 5 km²).
 * Fetched once per session and shared between every map instance; rings are
 * simplified lightly for rendering (0.15 km ≈ 5 px at the map's max zoom).
 */
import * as React from 'react'
import { api } from '@/services/api'
import type { PsrOut } from '@/types/api'

let cache: PsrOut[] | null = null
let inflight: Promise<PsrOut[]> | null = null

export function simplifyRing(ring: number[][], tol = 0.15): number[][] {
  if (ring.length <= 4) return ring
  const out = [ring[0]]
  let last = ring[0]
  for (let i = 1; i < ring.length - 1; i++) {
    const [x, y] = ring[i]
    if ((x - last[0]) ** 2 + (y - last[1]) ** 2 > tol * tol) {
      out.push(ring[i])
      last = ring[i]
    }
  }
  out.push(ring[ring.length - 1])
  return out.length < 4 ? ring : out
}

export interface PsrShape {
  psr: PsrOut
  positions: [number, number][][]
}

export function toShape(psr: PsrOut): PsrShape {
  const positions = psr.rings.map((ring) => {
    const simple = simplifyRing(ring)
    return simple.map(([x, y]) => [y, x] as [number, number])
  })
  return { psr, positions }
}

export function usePsrs(): { shapes: PsrShape[]; error: string | null } {
  const [state, setState] = React.useState<{ shapes: PsrShape[]; error: string | null }>(
    cache ? { shapes: [], error: null } : { shapes: [], error: null },
  )
  const ready = Boolean(cache)
  React.useEffect(() => {
    if (cache) return
    let alive = true
    inflight ??= api.psrs({ minAreaKm2: 5, maxLat: -80 }).then((d) => {
      cache = d
      inflight = null
      return d
    })
    inflight
      .then((d) => {
        if (alive) setState({ shapes: d.map(toShape), error: null })
      })
      .catch(() => {
        inflight = null
        if (alive) setState({ shapes: [], error: 'PSR layer unavailable' })
      })
    return () => {
      alive = false
    }
  }, [ready])
  return state
}
