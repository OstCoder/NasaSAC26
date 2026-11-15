import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AppConfig, RequirementEvaluation, Site } from '@/types/api'

const { requirementsMock } = vi.hoisted(() => ({ requirementsMock: vi.fn() }))

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return { ...actual, api: { ...actual.api, requirements: requirementsMock } }
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
  },
  simulation: {
    supported_start_utc: '2026-12-01T00:00:00Z',
    supported_end_utc: '2026-12-18T23:59:59Z',
    default_landing_utc: '2026-12-01T00:00:00Z',
    landing_presets: [],
    default_duration_hours: 168,
    min_duration_hours: 1,
    max_duration_hours: 708,
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

import { CandidateComparison } from './CandidateComparison'
import { ApiError } from '@/services/api'

function evaluation(
  site: Site,
  values: { sun: number | null; earth: number | null; blackout: number | null },
  statuses: { sun: 'met' | 'not_met' | 'unknown'; earth: 'met' | 'not_met' | 'unknown'; blackout: 'met' | 'not_met' | 'unknown' },
): RequirementEvaluation {
  const check = (
    id: string,
    label: string,
    unit: '%' | 'h',
    comparison: 'at_least' | 'at_most',
    threshold: number,
    value: number | null,
    status: 'met' | 'not_met' | 'unknown',
  ) => ({ id, label, unit, comparison, threshold, value, status, detail: `${label} detail` })
  const checks = [
    check('min_sun_visible_pct', 'Minimum sunlight', '%', 'at_least', 60, values.sun, statuses.sun),
    check('min_earth_visible_pct', 'Minimum Earth visibility', '%', 'at_least', 50, values.earth, statuses.earth),
    check('max_earth_blackout_hours', 'Maximum Earth blackout', 'h', 'at_most', 12, values.blackout, statuses.blackout),
  ]
  return {
    location: {
      site_id: site.id,
      name: site.name,
      latitude_deg: site.latitude_deg,
      longitude_deg: site.longitude_deg,
      is_custom: false,
      height_m: 2,
    },
    landing_utc: '2026-12-01T00:00:00Z',
    duration_hours: 168,
    requirements_source: 'test',
    checks,
    satisfied: checks.some((c) => c.status === 'not_met')
      ? false
      : checks.some((c) => c.status === 'unknown')
        ? null
        : true,
    psr_preference: 'optional',
    notes: [],
  }
}

const values = {
  A: { sun: 70, earth: 55, blackout: 8 },
  B: { sun: 66, earth: 62, blackout: 14 },
  C: { sun: 75, earth: 58, blackout: 5 },
}

const statuses = (v: { sun: number | null; earth: number | null; blackout: number | null }) => ({
  sun: v.sun != null && v.sun >= 60 ? 'met' as const : 'not_met' as const,
  earth: v.earth != null && v.earth >= 50 ? 'met' as const : 'not_met' as const,
  blackout: v.blackout != null && v.blackout <= 12 ? 'met' as const : 'not_met' as const,
})

beforeEach(() => {
  requirementsMock.mockReset()
  requirementsMock.mockImplementation((input: { location: { site_id: string } }) => {
    const site = sites.find((s) => s.id === input.location.site_id)!
    const v = values[site.id as keyof typeof values]
    return Promise.resolve(evaluation(site, v, statuses(v)))
  })
})

describe('CandidateComparison', () => {
  it('evaluates all three candidates over the same window and thresholds', async () => {
    render(<CandidateComparison />)
    fireEvent.click(screen.getByRole('button', { name: 'Compare all candidates' }))

    await waitFor(() => expect(screen.getAllByText('Shackleton Rim').length).toBeGreaterThan(0))
    expect(screen.getAllByText('Connecting Ridge').length).toBeGreaterThan(0)
    expect(screen.getAllByText('de Gerlache Rim').length).toBeGreaterThan(0)
    expect(requirementsMock).toHaveBeenCalledTimes(3)

    const [input, thresholds] = requirementsMock.mock.calls[0]
    expect(input).toMatchObject({
      landing_utc: '2026-12-01T00:00:00Z',
      duration_hours: 168,
      mode: 'demo',
      location: { site_id: 'A' },
    })
    expect(thresholds).toEqual({
      min_sun_visible_pct: 60,
      min_earth_visible_pct: 50,
      max_earth_blackout_hours: 12,
      max_darkness_hours: 16,
    })
    expect(requirementsMock.mock.calls[1][0].location.site_id).toBe('B')
    expect(requirementsMock.mock.calls[2][0].location.site_id).toBe('C')
  })

  it('reports a best-per-measure summary without inventing an overall winner', async () => {
    render(<CandidateComparison />)
    fireEvent.click(screen.getByRole('button', { name: 'Compare all candidates' }))

    await waitFor(() => expect(screen.getByText(/Most sunlight:/)).toBeTruthy())
    expect(screen.getByText(/Most sunlight:/).textContent).toContain('de Gerlache Rim (75%)')
    expect(screen.getByText(/Most Earth visibility:/).textContent).toContain('Connecting Ridge (62%)')
    expect(screen.getByText(/Shortest Earth blackout:/).textContent).toContain('de Gerlache Rim (5.0 h)')
    expect(screen.getAllByText('highest')).toHaveLength(2)
    expect(screen.getByText('shortest')).toBeTruthy()
  })

  it('shows UNDECIDED when a requirement cannot be evaluated and never counts it as a pass', async () => {
    requirementsMock.mockImplementation((input: { location: { site_id: string } }) => {
      const site = sites.find((s) => s.id === input.location.site_id)!
      if (site.id !== 'B') {
        const v = values[site.id as keyof typeof values]
        return Promise.resolve(evaluation(site, v, statuses(v)))
      }
      const v = { sun: 66, earth: null, blackout: 10 }
      return Promise.resolve(
        evaluation(site, v, { sun: 'met', earth: 'unknown', blackout: 'unknown' }),
      )
    })

    render(<CandidateComparison />)
    fireEvent.click(screen.getByRole('button', { name: 'Compare all candidates' }))

    await waitFor(() => expect(screen.getAllByText('Shackleton Rim').length).toBeGreaterThan(0))
    expect(screen.getAllByText('UNDECIDED').length).toBeGreaterThan(0)
    expect(screen.getAllByText('undecided').length).toBeGreaterThan(0)
    expect(screen.getAllByText('meets all').length).toBeGreaterThanOrEqual(2)
  })

  it('surfaces a backend failure instead of showing stale or assumed values', async () => {
    requirementsMock.mockRejectedValue(
      new ApiError(0, { code: 'BACKEND_UNREACHABLE', message: 'Cannot reach the backend', details: {} }),
    )

    render(<CandidateComparison />)
    fireEvent.click(screen.getByRole('button', { name: 'Compare all candidates' }))

    await waitFor(() => expect(screen.getByText('Backend not reachable')).toBeTruthy())
    expect(screen.queryByText(/Most sunlight:/)).toBeNull()
  })
})
