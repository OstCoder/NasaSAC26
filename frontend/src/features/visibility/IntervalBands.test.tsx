import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { IntervalBands } from './IntervalBands'
import type { IntervalSet } from '@/types/api'

const intervals: IntervalSet = {
  sun_visible: [
    { start_utc: '2026-12-01T00:00:00Z', end_utc: '2026-12-02T00:00:00Z', duration_hours: 24, clipped_start: false, clipped_end: false },
  ],
  earth_visible: [
    { start_utc: '2026-12-02T00:00:00Z', end_utc: '2026-12-03T00:00:00Z', duration_hours: 24, clipped_start: false, clipped_end: false },
  ],
  both_visible: [],
  sun_blocked: [],
  earth_blocked: [],
  neither_visible: [],
}

describe('IntervalBands', () => {
  it('labels every row and exposes the active interval without relying on colour', () => {
    const { container } = render(
      <IntervalBands
        intervals={intervals}
        windowStart="2026-12-01T00:00:00Z"
        windowEnd="2026-12-08T00:00:00Z"
        cursorFrac={0.1}
      />,
    )

    expect(screen.getByText('Sun')).toBeTruthy()
    expect(screen.getByText('Earth')).toBeTruthy()
    expect(screen.getByText('Both')).toBeTruthy()
    // 0.1 of seven days is inside the 1–2 Dec sunlight interval.
    expect(container.querySelector('[aria-current="time"]')).toBeTruthy()
  })

  it('moves the inspection cursor from the keyboard', () => {
    const onPick = vi.fn()
    render(
      <IntervalBands
        intervals={intervals}
        windowStart="2026-12-01T00:00:00Z"
        windowEnd="2026-12-08T00:00:00Z"
        cursorFrac={0.5}
        onPick={onPick}
      />,
    )

    fireEvent.keyDown(screen.getByRole('button', { name: /Sun visibility bands/ }), {
      key: 'ArrowRight',
    })
    expect(onPick).toHaveBeenCalledWith(0.51)
  })
})
