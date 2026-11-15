import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AppConfig, RequirementEvaluation } from '@/types/api'

const { requirementsMock } = vi.hoisted(() => ({ requirementsMock: vi.fn() }))

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return { ...actual, api: { ...actual.api, requirements: requirementsMock } }
})

const config = {
  requirements: { min_sun_visible_pct: 60, min_earth_visible_pct: 50, max_earth_blackout_hours: 12 },
} as unknown as AppConfig

const draftA = {
  location: { site_id: 'A' },
  locationName: 'Shackleton Rim',
  landing_utc: '2026-12-01T00:00:00Z',
  duration_hours: 168,
}

vi.mock('@/hooks/useAppContext', () => ({
  useApp: () => ({
    config,
    sites: [],
    features: {},
    mode: 'demo',
    setMode: vi.fn(),
    draftA,
    setDraftA: vi.fn(),
    draftB: draftA,
    setDraftB: vi.fn(),
  }),
  siteDraftLocation: vi.fn(),
}))

import { RequirementTuner } from './RequirementTuner'

const result: RequirementEvaluation = {
  location: {
    site_id: 'A',
    name: 'Shackleton Rim',
    latitude_deg: -89.9,
    longitude_deg: 0,
    is_custom: false,
    height_m: 2,
  },
  landing_utc: '2026-12-01T00:00:00Z',
  duration_hours: 168,
  requirements_source: 'user-adjusted demonstration targets',
  checks: [
    {
      id: 'min_sun_visible_pct',
      label: 'Minimum sunlight availability',
      unit: '%',
      comparison: 'at_least',
      threshold: 75,
      value: 70,
      status: 'not_met',
      detail: 'Sunlight is below the selected target.',
    },
  ],
  satisfied: false,
  psr_preference: 'optional',
  notes: [],
}

beforeEach(() => {
  requirementsMock.mockReset()
  requirementsMock.mockResolvedValue(result)
})

describe('RequirementTuner', () => {
  it('blocks invalid thresholds before sending a request', () => {
    render(<RequirementTuner />)
    const sun = screen.getByLabelText('Minimum sunlight (%)')

    fireEvent.change(sun, { target: { value: '140' } })
    expect(screen.getByText('Minimum sunlight must be between 0 and 100%.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Check requirements' })).toHaveProperty('disabled', true)
    expect(requirementsMock).not.toHaveBeenCalled()
  })

  it('sends adjusted targets and reports a failed constraint', async () => {
    render(<RequirementTuner />)
    fireEvent.change(screen.getByLabelText('Minimum sunlight (%)'), { target: { value: '75' } })
    fireEvent.click(screen.getByRole('button', { name: 'Check requirements' }))

    await waitFor(() => expect(requirementsMock).toHaveBeenCalledTimes(1))
    expect(requirementsMock.mock.calls[0][1]).toMatchObject({ min_sun_visible_pct: 75 })
    await screen.findByText('One or more constraints fail')
    expect(screen.getByText('FAIL')).toBeTruthy()
  })
})
