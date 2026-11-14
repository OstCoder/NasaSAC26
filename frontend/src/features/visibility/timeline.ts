/** View-only time domain for the visibility chart. */
export function zoomDomain(
  windowStart: number,
  windowEnd: number,
  cursor: number,
  zoomHours: number | null,
): [number, number] {
  if (!(windowEnd > windowStart)) return [windowStart, windowEnd]
  const span = zoomHours === null ? 0 : zoomHours * 3_600_000
  if (span <= 0 || span >= windowEnd - windowStart) return [windowStart, windowEnd]

  // Keep the inspected sample in view, then pull the window back inside the
  // mission so an edge sample never produces an out-of-range domain.
  const centre = Math.min(windowEnd, Math.max(windowStart, cursor))
  const start = Math.max(windowStart, centre - span / 2)
  const end = Math.min(windowEnd, start + span)
  return [Math.max(windowStart, end - span), end]
}
