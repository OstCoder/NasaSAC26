import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Animates a number from 0 to `value` over `duration` ms. Falls back to the
 * static value when prefers-reduced-motion is set. Keeps tabular numerals.
 */
export function CountUp({
  value,
  duration = 600,
  decimals = 0,
  className,
}: {
  value: number
  duration?: number
  decimals?: number
  className?: string
}) {
  const [display, setDisplay] = React.useState(0)
  const reduced = React.useRef(false)

  React.useEffect(() => {
    reduced.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced.current) { setDisplay(value); return }
    let raf = 0
    const start = performance.now()
    const from = display
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(from + (value - from) * eased)
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration])

  return <span className={cn('num', className)}>{display.toFixed(decimals)}</span>
}