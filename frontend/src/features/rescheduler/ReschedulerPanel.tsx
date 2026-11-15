import { ArrowRight, LoaderCircle } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Field, Input } from '@/components/ui/field'
import { DeltaTable } from '@/features/comparison/DeltaTable'
import { PairedBands } from '@/features/comparison/PairedBands'
import { TradeoffNotes } from '@/features/comparison/TradeoffNotes'
import { ScenarioEditor, rangeProblem } from '@/features/mission-planner/ScenarioEditor'
import { useApiResource } from '@/hooks/useApiResource'
import { useApp } from '@/hooks/useAppContext'
import { fmtHours, inputToIso, isoToInput } from '@/lib/format'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type {
  DelayPowerComparison,
  DelayRequirementComparison,
  RequirementStatus,
  RescheduleResult,
} from '@/types/api'

const SHIFTS_DAYS = [-7, -1, 1, 3, 7, 14]
const shift = (iso: string, days: number) =>
  new Date(Date.parse(iso) + days * 86_400_000).toISOString().slice(0, 19) + 'Z'

const STATUS_STYLE: Record<RequirementStatus, string> = {
  met: 'text-both',
  not_met: 'text-sun',
  unknown: 'text-faint',
}
const STATUS_WORD: Record<RequirementStatus, string> = {
  met: 'PASS',
  not_met: 'FAIL',
  unknown: 'UNDECIDED',
}
const num = (value: number | null | undefined, digits = 0) =>
  value == null ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits })

function DelayRequirements({ comparison }: { comparison: DelayRequirementComparison }) {
  const original = new Map(comparison.original.checks.map((check) => [check.id, check]))
  return (
    <section aria-label="Requirement verdict changes" className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Requirement verdicts</h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-xs">
          <thead>
            <tr className="text-faint">
              <th className="px-2 py-1 font-medium">Requirement</th>
              <th className="px-2 py-1 font-medium">Original</th>
              <th className="px-2 py-1 font-medium">Proposed</th>
            </tr>
          </thead>
          <tbody>
            {comparison.proposed.checks.map((check) => {
              const before = original.get(check.id)
              return (
                <tr key={check.id}>
                  <td className="border-t border-rule-soft px-2 py-1.5 text-ink">{check.label}</td>
                  <td className={cn('border-t border-rule-soft px-2 py-1.5', before ? STATUS_STYLE[before.status] : 'text-faint')}>
                    {before ? STATUS_WORD[before.status] : '—'}
                  </td>
                  <td className={cn('border-t border-rule-soft px-2 py-1.5', STATUS_STYLE[check.status])}>
                    {STATUS_WORD[check.status]}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">{comparison.summary}</p>
    </section>
  )
}

function DelayPower({ comparison }: { comparison: DelayPowerComparison }) {
  const a = comparison.original
  const b = comparison.proposed
  if (!comparison.available || !a.battery || !b.battery) {
    return (
      <section aria-label="Power and battery comparison" className="space-y-1">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Power and battery</h3>
        <p className="text-xs text-muted">{comparison.summary}</p>
      </section>
    )
  }
  const rows = [
    ['Array energy', 'Wh', a.array_energy_wh, b.array_energy_wh],
    ['Net energy', 'Wh', a.net_wh, b.net_wh],
    ['Minimum battery', '%', a.battery.min_soc_pct, b.battery.min_soc_pct],
    ['Unserved load', 'Wh', a.battery.unserved_wh, b.battery.unserved_wh],
  ] as const
  return (
    <section aria-label="Power and battery comparison" className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Power and battery</h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-xs">
          <thead>
            <tr className="text-faint">
              <th className="px-2 py-1 font-medium">Metric</th>
              <th className="px-2 py-1 text-right font-medium">Original</th>
              <th className="px-2 py-1 text-right font-medium">Proposed</th>
              <th className="px-2 py-1 text-right font-medium">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, unit, before, after]) => {
              const key = label === 'Array energy' ? 'array_energy_wh'
                : label === 'Net energy' ? 'net_wh'
                  : label === 'Minimum battery' ? 'min_soc_pct' : 'unserved_wh'
              const delta = comparison.deltas[key]
              return (
                <tr key={label}>
                  <td className="border-t border-rule-soft px-2 py-1.5 text-ink">{label}</td>
                  <td className="num border-t border-rule-soft px-2 py-1.5 text-right">{num(before, 1)} {unit}</td>
                  <td className="num border-t border-rule-soft px-2 py-1.5 text-right">{num(after, 1)} {unit}</td>
                  <td className="num border-t border-rule-soft px-2 py-1.5 text-right">
                    {delta == null ? '—' : `${delta > 0 ? '+' : ''}${num(delta, 1)} ${unit}`}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">{comparison.summary}</p>
      <p className="text-[11px] text-faint">{comparison.notes.join(' ')}</p>
    </section>
  )
}

/** Same site and duration, two landing dates: what changes if the mission slips? */
export function ReschedulerPanel() {
  const { draftA, setDraftA, mode, setMode, config } = useApp()
  const sim = config.simulation
  const [proposed, setProposed] = React.useState(() => shift(draftA.landing_utc, 3))

  const body = {
    location: draftA.location,
    original_landing_utc: draftA.landing_utc,
    proposed_landing_utc: proposed,
    duration_hours: draftA.duration_hours,
    mode,
  }
  const problem =
    rangeProblem(draftA, sim.supported_start_utc, sim.supported_end_utc) ||
    rangeProblem({ ...draftA, landing_utc: proposed }, sim.supported_start_utc, sim.supported_end_utc)
  const res = useApiResource<RescheduleResult>(problem ? null : JSON.stringify(body), () => api.reschedule(body), 350)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Reschedule a mission" description="Keep the site and duration, move the landing date, and see how visibility, requirements and the committed power model change." />
        <CardContent className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
          <div className="space-y-3">
            <ScenarioEditor draft={draftA} onChange={setDraftA} dense />
          </div>
          <ArrowRight className="mx-auto hidden size-5 self-center text-faint lg:block" aria-hidden />
          <div className="space-y-3">
            <Field label="Proposed landing time (UTC)">
              <Input type="datetime-local" value={isoToInput(proposed)} min={isoToInput(sim.supported_start_utc)}
                max={isoToInput(sim.supported_end_utc)} onChange={(e) => e.target.value && setProposed(inputToIso(e.target.value))} />
            </Field>
            <div>
              <p className="mb-1 text-[13px] text-muted">Shift from the original date</p>
              <div className="flex flex-wrap gap-1">
                {SHIFTS_DAYS.map((d) => {
                  const target = shift(draftA.landing_utc, d)
                  return (
                    <button key={d} onClick={() => setProposed(target)}
                      className={cn('num h-8 rounded-md border px-2.5 text-xs transition-colors',
                        target === proposed ? 'border-signal/60 bg-signal/10 text-ink' : 'border-rule text-muted hover:text-ink')}>
                      {d > 0 ? '+' : '−'}{Math.abs(d)} d
                    </button>
                  )
                })}
              </div>
            </div>
            {problem && <p className="text-xs text-alert">{problem}</p>}
          </div>
        </CardContent>
      </Card>

      {res.error && (
        <ErrorNotice
          error={res.error}
          onUseDemo={mode !== 'demo' ? () => setMode('demo') : undefined}
          onRetry={res.retry}
        />
      )}
      {res.loading && !res.data && (
        <p className="flex items-center gap-2 text-sm text-muted"><LoaderCircle className="size-4 animate-spin" /> Recomputing…</p>
      )}

      {res.data && !res.error && (
        <Card className={res.loading ? 'opacity-70 transition-opacity' : ''}>
          <CardHeader
            title={`Effect of moving the landing ${Math.abs(res.data.shift_hours / 24).toFixed(1).replace(/\.0$/, '')} days ${res.data.shift_hours >= 0 ? 'later' : 'earlier'}`}
            description={`${res.data.comparison.a.location.name}, ${fmtHours(res.data.comparison.a.duration_hours)} mission.`}
          />
          <CardContent className="space-y-6">
            <DeltaTable deltas={res.data.headline_changes} aLabel="Original" bLabel="Proposed" />
            <PairedBands a={res.data.comparison.a} b={res.data.comparison.b} aLabel="Original" bLabel="Proposed" />
            {res.data.requirements && <DelayRequirements comparison={res.data.requirements} />}
            {res.data.power && <DelayPower comparison={res.data.power} />}
            <TradeoffNotes result={res.data.comparison} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
