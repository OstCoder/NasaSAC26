import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AppConfig, DecisionResult, Site } from '@/types/api'

const { decisionMock } = vi.hoisted(() => ({ decisionMock: vi.fn() }))

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return { ...actual, api: { ...actual.api, decision: decisionMock } }
})

const sites = [
  { id: 'A', name: 'Shackleton Rim', latitude_deg: -89.9, longitude_deg: 0, region: '', description: '', coordinate_note: '', tags: [], source: '' },
  { id: 'B', name: 'Connecting Ridge', latitude_deg: -89.45, longitude_deg: 222.7, region: '', description: '', coordinate_note: '', tags: [], source: '' },
  { id: 'C', name: 'de Gerlache Rim', latitude_deg: -88.5, longitude_deg: 273.4, region: '', description: '', coordinate_note: '', tags: [], source: '' },
] as Site[]

const config = {
  mission: { candidate_sites: ['A', 'B', 'C'] },
  requirements: {
    min_sun_visible_pct: 60,
    min_earth_visible_pct: 50,
    max_earth_blackout_hours: 12,
    max_darkness_hours: 16,
    power_demand_w: 40,
    psr_proximity: 'preferred',
    basis: 'test',
  },
  simulation: {
    supported_start_utc: '2026-12-01T00:00:00Z',
    supported_end_utc: '2026-12-18T23:59:59Z',
    default_landing_utc: '2026-12-01T00:00:00Z',
    landing_presets: [],
    default_duration_hours: 168,
    min_duration_hours: 1,
    max_duration_hours: 1440,
  },
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
    sites,
    features: { custom_coordinates: true },
    mode: 'demo',
    setMode: vi.fn(),
    draftA,
    setDraftA: vi.fn(),
    draftB: draftA,
    setDraftB: vi.fn(),
  }),
  siteDraftLocation: (site: Site) => ({ location: { site_id: site.id }, locationName: site.name }),
}))

import { DecisionDashboard } from './DecisionDashboard'

const check = (
  id: string,
  label: string,
  unit: '%' | 'h' | 'Wh',
  comparison: 'at_least' | 'at_most',
  threshold: number,
  value: number | null,
  status: 'met' | 'not_met' | 'unknown',
) => ({ id, label, unit, comparison, threshold, value, status, detail: `${label} detail` })

function site(
  id: string,
  name: string,
  status: 'pass' | 'fail' | 'unknown',
  rank: number | null,
  score: number | null,
  values: { sun: number; earth: number; blackout: number; darkness: number },
): DecisionResult['sites'][number] {
  const checks = [
    check('min_sun_visible_pct', 'Minimum sunlight', '%', 'at_least', 60, values.sun, status === 'pass' ? 'met' : status === 'fail' ? 'not_met' : 'unknown'),
    check('min_earth_visible_pct', 'Minimum Earth visibility', '%', 'at_least', 50, values.earth, status === 'pass' ? 'met' : status === 'fail' ? 'not_met' : 'unknown'),
    check('max_earth_blackout_hours', 'Maximum Earth blackout', 'h', 'at_most', 12, values.blackout, status === 'pass' ? 'met' : status === 'fail' ? 'not_met' : 'unknown'),
    check('max_darkness_hours', 'Maximum darkness', 'h', 'at_most', 16, values.darkness, status === 'pass' ? 'met' : status === 'fail' ? 'not_met' : 'unknown'),
    check('power_system_survives', 'Battery reserve throughout mission', 'Wh', 'at_most', 0, 0, status === 'pass' ? 'met' : status === 'fail' ? 'not_met' : 'unknown'),
  ]
  return {
    site_id: id,
    name,
    latitude_deg: -89,
    longitude_deg: 0,
    status,
    satisfied: status === 'pass' ? true : status === 'fail' ? false : null,
    checks,
    metrics: {
      sun_visible_pct: values.sun,
      earth_visible_pct: values.earth,
      both_visible_pct: Math.min(values.sun, values.earth),
      longest_sun_blackout_hours: values.darkness,
      longest_earth_blackout_hours: values.blackout,
      longest_no_simultaneous_hours: values.blackout,
    },
    rank,
    score,
    score_components: {},
    power: {
      available: true,
      window: 'initial',
      load_w: 40,
      load_wh: 6720,
      array_energy_wh: 9000,
      net_wh: 2280,
      battery: {
        capacity_wh: 1200,
        usable_wh: 960,
        initial_soc_pct: 100,
        min_soc_pct: 72,
        final_soc_pct: 88,
        unserved_wh: 0,
        depleted: false,
        reserve_pct: 20,
        reserve_respected: true,
        verdict: 'Battery stays above reserve.',
      },
      reason: null,
    },
    nearest_psr: {
      psr_id: `psr-${id}`,
      label: `PSR ${id}`,
      distance_km: 4.2,
      area_km2: 20,
      centroid_latitude_deg: -89.5,
      centroid_longitude_deg: 10,
    },
    psrs_within_10_km: 1,
    reasons: status === 'pass' ? ['Meets every selected mission constraint in this window.'] : ['Fails a selected constraint.'],
    risks: status === 'pass' ? [] : ['A failed check is never treated as favourable.'],
    provenance: 'synthetic',
  }
}

const result: DecisionResult = {
  schema: 'lunanav.mission_decision.v1',
  landing_utc: '2026-12-01T00:00:00Z',
  duration_hours: 168,
  mode: 'demo',
  thresholds: {
    min_sun_visible_pct: 60,
    min_earth_visible_pct: 50,
    max_earth_blackout_hours: 12,
    max_darkness_hours: 16,
    power_demand_w: 40,
  },
  weights: { sunlight: 0.4, earth_visibility: 0.3, communication: 0.2, science: 0 },
  recommendation: {
    status: 'ranked',
    top_site_id: 'C',
    top_site_name: 'de Gerlache Rim',
    ranked_site_ids: ['C', 'A'],
    summary: 'de Gerlache Rim ranks first of 2 eligible candidates.',
  },
  sites: [
    site('A', 'Shackleton Rim', 'pass', 2, 55.2, { sun: 70, earth: 55, blackout: 8, darkness: 9 }),
    site('B', 'Connecting Ridge', 'fail', null, null, { sun: 66, earth: 40, blackout: 14, darkness: 20 }),
    site('C', 'de Gerlache Rim', 'pass', 1, 81.4, { sun: 75, earth: 58, blackout: 5, darkness: 6 }),
  ],
  notes: [
    'Only candidates that pass every selected check are ranked.',
    'PSR proximity is not proof of water ice.',
  ],
}

beforeEach(() => {
  decisionMock.mockReset()
  decisionMock.mockResolvedValue(result)
})

describe('DecisionDashboard', () => {
  it('sends all five requirements and shows the ranked recommendation', async () => {
    render(<DecisionDashboard />)

    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(1))
    const body = decisionMock.mock.calls[0][0]
    expect(body).toMatchObject({
      landing_utc: '2026-12-01T00:00:00Z',
      duration_hours: 168,
      thresholds: {
        min_sun_visible_pct: 60,
        min_earth_visible_pct: 50,
        max_earth_blackout_hours: 12,
        max_darkness_hours: 16,
        power_demand_w: 40,
      },
    })
    await screen.findByText('de Gerlache Rim is top-ranked')
    expect(screen.getAllByText(/fails at least one constraint/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Priority fit/i).length).toBeGreaterThan(0)
  })

  it('updates the request when the mission priority changes', async () => {
    render(<DecisionDashboard />)
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: 'Communications first' }))
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(2))
    expect(decisionMock.mock.calls[1][0].weights).toEqual({
      sunlight: 0.15,
      earth_visibility: 0.25,
      communication: 0.6,
      science: 0,
    })
  })

  it('opens science exploration mode with PSR context and science weights', async () => {
    render(<DecisionDashboard />)
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(1))

    decisionMock.mockResolvedValueOnce({
      ...result,
      weights: { sunlight: 0.3, earth_visibility: 0.2, communication: 0.1, science: 0.4 },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Science focus' }))
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(2))

    expect(decisionMock.mock.calls[1][0].weights).toEqual({
      sunlight: 0.3,
      earth_visibility: 0.2,
      communication: 0.1,
      science: 0.4,
    })
    expect(await screen.findByText('Science context')).toBeTruthy()
    expect(screen.getAllByText(/nearest mapped PSR/).length).toBeGreaterThan(0)
    expect(screen.getByText(/not a traverse plan/i)).toBeTruthy()
  })

  it('keeps the censored blackout check advisory by default and can require it', async () => {
    render(<DecisionDashboard />)
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(1))
    expect(decisionMock.mock.calls[0][0].optional_checks).toEqual(['max_earth_blackout_hours'])
    expect(screen.getByLabelText('Require for eligibility')).toHaveProperty('checked', false)

    fireEvent.click(screen.getByLabelText('Require for eligibility'))
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(2))
    expect(decisionMock.mock.calls[1][0].optional_checks).toEqual([])
    expect(screen.getByLabelText('Require for eligibility')).toHaveProperty('checked', true)
  })

  it('hides the previous recommendation while a changed date is evaluating', async () => {
    render(<DecisionDashboard />)
    await screen.findByText('de Gerlache Rim is top-ranked')

    let resolveNext: ((value: DecisionResult) => void) | undefined
    decisionMock.mockImplementationOnce(
      () => new Promise<DecisionResult>((resolve) => { resolveNext = resolve }),
    )
    fireEvent.change(screen.getByLabelText('Landing time (UTC)'), {
      target: { value: '2026-12-11T00:00' },
    })

    await waitFor(() => expect(screen.queryByText('de Gerlache Rim is top-ranked')).toBeNull())
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(2))
    resolveNext?.({ ...result, landing_utc: '2026-12-11T00:00:00Z' })
    await screen.findByText('de Gerlache Rim is top-ranked')
  })

  it('blocks an invalid power demand before calling the backend', async () => {
    render(<DecisionDashboard />)
    await waitFor(() => expect(decisionMock).toHaveBeenCalledTimes(1))

    fireEvent.change(screen.getByLabelText('Average power demand (W)'), { target: { value: '100001' } })
    expect(screen.getByText('Average power demand must be between 0 and 100,000 W.')).toBeTruthy()
    expect(decisionMock).toHaveBeenCalledTimes(1)
  })
})
