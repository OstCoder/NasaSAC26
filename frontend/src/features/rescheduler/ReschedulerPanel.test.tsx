import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AppConfig, RescheduleResult } from '@/types/api'

const { rescheduleMock } = vi.hoisted(() => ({ rescheduleMock: vi.fn() }))

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return { ...actual, api: { ...actual.api, reschedule: rescheduleMock } }
})

vi.mock('@/features/mission-planner/ScenarioEditor', () => ({
  ScenarioEditor: () => <div data-testid="scenario-editor" />,
  rangeProblem: () => null,
}))

vi.mock('@/features/comparison/DeltaTable', () => ({
  DeltaTable: () => <div data-testid="delta-table" />,
}))
vi.mock('@/features/comparison/PairedBands', () => ({
  PairedBands: () => <div data-testid="paired-bands" />,
}))
vi.mock('@/features/comparison/TradeoffNotes', () => ({
  TradeoffNotes: () => <div data-testid="tradeoff-notes" />,
}))

const config = {
  simulation: {
    supported_start_utc: '2026-12-01T00:00:00Z',
    supported_end_utc: '2026-12-18T23:59:59Z',
  },
} as unknown as AppConfig

const draftA = {
  location: { site_id: 'de-gerlache-rim' },
  locationName: 'de Gerlache Rim',
  landing_utc: '2026-12-01T00:00:00Z',
  duration_hours: 168,
}

vi.mock('@/hooks/useAppContext', () => ({
  useApp: () => ({
    config,
    draftA,
    setDraftA: vi.fn(),
    mode: 'demo',
    setMode: vi.fn(),
  }),
}))

import { ReschedulerPanel } from './ReschedulerPanel'

const status = (id: string, label: string, value: 'met' | 'not_met' | 'unknown') => ({
  id,
  label,
  unit: '%',
  comparison: 'at_least' as const,
  threshold: 50,
  value: 60,
  status: value,
  required: true,
  detail: label,
})

const result = {
  shift_hours: 240,
  comparison: {
    a: { location: { name: 'de Gerlache Rim' }, duration_hours: 168 },
    b: { location: { name: 'de Gerlache Rim' }, duration_hours: 168 },
  },
  headline_changes: [],
  requirements: {
    original: { checks: [status('min_sun_visible_pct', 'Minimum sunlight', 'met')] },
    proposed: { checks: [status('min_sun_visible_pct', 'Minimum sunlight', 'not_met')] },
    new_failures: ['Minimum sunlight'],
    improvements: [],
    summary: 'New failures: Minimum sunlight. Improvements: none.',
  },
  power: {
    available: true,
    original: {
      available: true,
      window: 'initial',
      load_w: 40,
      load_wh: 6720,
      array_energy_wh: 10000,
      net_wh: 3280,
      reason: null,
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
    },
    proposed: {
      available: true,
      window: 'alternative',
      load_w: 40,
      load_wh: 6720,
      array_energy_wh: 9000,
      net_wh: 2280,
      reason: null,
      battery: {
        capacity_wh: 1200,
        usable_wh: 960,
        initial_soc_pct: 100,
        min_soc_pct: 61,
        final_soc_pct: 80,
        unserved_wh: 0,
        depleted: false,
        reserve_pct: 20,
        reserve_respected: true,
        verdict: 'Battery stays above reserve.',
      },
    },
    deltas: { array_energy_wh: -1000, net_wh: -1000, min_soc_pct: -11, unserved_wh: 0 },
    summary: 'Array energy 10000 → 9000 Wh; minimum battery 72.0% → 61.0%; unserved 0 → 0 Wh.',
    notes: ['Power is reported for the recommended vertical azimuth-tracking array.'],
  },
} as unknown as RescheduleResult

beforeEach(() => {
  rescheduleMock.mockReset()
  rescheduleMock.mockResolvedValue(result)
})

describe('ReschedulerPanel', () => {
  it('shows requirement verdict changes and power/battery deltas', async () => {
    render(<ReschedulerPanel />)

    expect(await screen.findByText('Requirement verdicts', {}, { timeout: 2000 })).toBeTruthy()
    expect(screen.getByText('New failures: Minimum sunlight. Improvements: none.')).toBeTruthy()
    expect(screen.getAllByText('PASS').length).toBeGreaterThan(0)
    expect(screen.getAllByText('FAIL').length).toBeGreaterThan(0)
    expect(screen.getByText('Power and battery')).toBeTruthy()
    expect(screen.getByText(/Array energy 10000/)).toBeTruthy()
    expect(screen.getAllByText('-1,000.0 Wh').length).toBeGreaterThan(0)
    expect(screen.getByText('-11.0 %')).toBeTruthy()
  })
})
