import { CheckCircle2, CircleHelp, RotateCcw, XCircle } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Field, Input } from '@/components/ui/field'
import { useApiResource } from '@/hooks/useApiResource'
import { useApp } from '@/hooks/useAppContext'
import { draftToInput } from '@/hooks/useScenario'
import { fmtHours, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type { RequirementEvaluation, RequirementStatus } from '@/types/api'

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

const fmtValue = (value: number | null, unit: string) =>
  value == null ? '—' : unit === '%' ? `${Math.round(value * 10) / 10}%` : fmtHours(value)

function StatusIcon({ status }: { status: RequirementStatus }) {
  const Icon = status === 'met' ? CheckCircle2 : status === 'not_met' ? XCircle : CircleHelp
  return <Icon className={cn('size-4', STATUS_STYLE[status])} aria-hidden />
}

/**
 * Phase 4 Task 8: run the same requirement engine the backend uses, but with
 * thresholds the user sets for this check. Targets are demonstration values —
 * never NASA flight requirements — and every value is still computed by the
 * metric registry, never typed in by hand.
 */
export function RequirementTuner() {
  const { config, draftA, mode } = useApp()
  const defaults = config.requirements
  const [sun, setSun] = React.useState(String(defaults.min_sun_visible_pct))
  const [earth, setEarth] = React.useState(String(defaults.min_earth_visible_pct))
  const [blackout, setBlackout] = React.useState(String(defaults.max_earth_blackout_hours))
  const [requested, setRequested] = React.useState(false)

  const sunNum = Number(sun)
  const earthNum = Number(earth)
  const blackoutNum = Number(blackout)
  const problem =
    sun.trim() === '' || !Number.isFinite(sunNum) || sunNum < 0 || sunNum > 100
      ? 'Minimum sunlight must be between 0 and 100%.'
      : earth.trim() === '' || !Number.isFinite(earthNum) || earthNum < 0 || earthNum > 100
        ? 'Minimum Earth visibility must be between 0 and 100%.'
        : blackout.trim() === '' || !Number.isFinite(blackoutNum) || blackoutNum < 0
          ? 'Maximum blackout must be zero or more hours.'
          : null

  // Any edit invalidates the previous verdict rather than letting it look current.
  React.useEffect(() => {
    setRequested(false)
  }, [draftA, sun, earth, blackout])

  const body = draftToInput(draftA, mode)
  const key =
    requested && !problem
      ? JSON.stringify({ body, thresholds: { sunNum, earthNum, blackoutNum } })
      : null
  const check = useApiResource<RequirementEvaluation>(
    key,
    (signal) =>
      api.requirements(
        body,
        {
          min_sun_visible_pct: sunNum,
          min_earth_visible_pct: earthNum,
          max_earth_blackout_hours: blackoutNum,
        },
        signal,
      ),
    0,
  )

  const reset = () => {
    setSun(String(defaults.min_sun_visible_pct))
    setEarth(String(defaults.min_earth_visible_pct))
    setBlackout(String(defaults.max_earth_blackout_hours))
    setRequested(false)
  }

  const result = check.data
  const satisfied = result?.satisfied
  const verdict =
    satisfied === true
      ? { word: 'All selected constraints met', tone: 'text-both', detail: 'Every check below passes for this scenario.' }
      : satisfied === false
        ? {
            word: 'One or more constraints fail',
            tone: 'text-sun',
            detail: 'This scenario does not satisfy all of the selected demonstration constraints.',
          }
        : satisfied === null
          ? {
              word: 'Undecided',
              tone: 'text-faint',
              detail: 'At least one check cannot be decided from this window; undecided is not a pass.',
            }
          : null

  return (
    <Card>
      <CardHeader
        title="Mission requirements check"
        description={`Adjusted for ${draftA.locationName}, landing ${fmtUtc(draftA.landing_utc)} UTC for ${fmtHours(draftA.duration_hours)}. Demonstration targets only — not NASA flight requirements.`}
        actions={
          <Button size="sm" variant="ghost" onClick={reset}>
            <RotateCcw /> Phase 1 targets
          </Button>
        }
      />
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Minimum sunlight (%)" hint="Share of the window with the Sun above the skyline">
            <Input
              type="number"
              min={0}
              max={100}
              step={1}
              value={sun}
              aria-invalid={problem !== null && (!Number.isFinite(sunNum) || sunNum < 0 || sunNum > 100)}
              onChange={(e) => setSun(e.target.value)}
            />
          </Field>
          <Field label="Minimum Earth visibility (%)" hint="Share of the window with Earth above the skyline">
            <Input
              type="number"
              min={0}
              max={100}
              step={1}
              value={earth}
              aria-invalid={problem !== null && (!Number.isFinite(earthNum) || earthNum < 0 || earthNum > 100)}
              onChange={(e) => setEarth(e.target.value)}
            />
          </Field>
          <Field label="Maximum communication blackout (h)" hint="Longest continuous Earth outage allowed">
            <Input
              type="number"
              min={0}
              step={1}
              value={blackout}
              aria-invalid={problem !== null && (!Number.isFinite(blackoutNum) || blackoutNum < 0)}
              onChange={(e) => setBlackout(e.target.value)}
            />
          </Field>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setRequested(true)} disabled={problem !== null || check.loading}>
            {check.loading ? 'Checking…' : 'Check requirements'}
          </Button>
          <p className="text-xs text-muted">
            Defaults: ≥ {defaults.min_sun_visible_pct}% Sun, ≥ {defaults.min_earth_visible_pct}% Earth, ≤{' '}
            {defaults.max_earth_blackout_hours} h blackout.
          </p>
        </div>
        {problem && <p className="text-xs text-alert">{problem}</p>}
        {check.error && <ErrorNotice error={check.error} />}

        {result && !check.error && (
          <div
            className={cn('space-y-3 rounded-lg border border-rule-soft p-3', check.loading && 'opacity-70')}
            role="region"
            aria-live="polite"
            aria-label="Mission requirement results"
          >
            <div>
              <p className={cn('font-display text-sm font-semibold', verdict?.tone)}>{verdict?.word}</p>
              <p className="text-xs text-muted">{verdict?.detail}</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-faint">
                    <th className="px-2 py-1 font-medium">Requirement</th>
                    <th className="px-2 py-1 font-medium">Measured</th>
                    <th className="px-2 py-1 font-medium">Target</th>
                    <th className="px-2 py-1 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {result.checks.map((c) => (
                    <tr key={c.id}>
                      <td className="border-t border-rule-soft px-2 py-1.5 text-ink">{c.label}</td>
                      <td className="num border-t border-rule-soft px-2 py-1.5">{fmtValue(c.value, c.unit)}</td>
                      <td className="num border-t border-rule-soft px-2 py-1.5">
                        {c.comparison === 'at_least' ? '≥' : '≤'} {fmtValue(c.threshold, c.unit)}
                      </td>
                      <td className="border-t border-rule-soft px-2 py-1.5">
                        <span className={cn('flex items-center gap-1.5 font-medium', STATUS_STYLE[c.status])}>
                          <StatusIcon status={c.status} />
                          {STATUS_WORD[c.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="space-y-1 text-xs text-muted">
              {result.checks.map((c) => (
                <li key={`${c.id}-detail`}>{c.detail}</li>
              ))}
            </ul>
            <p className="text-xs text-faint">
              Source: {result.requirements_source}. Sunlight is not available power; Earth visibility is
              not a working communications link.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
