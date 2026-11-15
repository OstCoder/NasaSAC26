import { AlertTriangle, CheckCircle2, CircleHelp, XCircle } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Field, Input } from '@/components/ui/field'
import { ScenarioEditor, rangeProblem } from '@/features/mission-planner/ScenarioEditor'
import { useApiResource } from '@/hooks/useApiResource'
import { useApp } from '@/hooks/useAppContext'
import { fmtHours, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type {
  RequirementCheck,
  RequirementEvaluation,
  RequirementStatus,
  Site,
} from '@/types/api'

const CHECK_IDS = {
  sun: 'min_sun_visible_pct',
  earth: 'min_earth_visible_pct',
  blackout: 'max_earth_blackout_hours',
} as const

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

interface Outcome {
  site: Site
  evaluation?: RequirementEvaluation
  error?: string
}

const checkFor = (evaluation: RequirementEvaluation | undefined, id: string) =>
  evaluation?.checks.find((check) => check.id === id)

const fmtValue = (check: RequirementCheck | undefined) => {
  if (check?.value == null) return '—'
  return check.unit === '%' ? `${Math.round(check.value * 10) / 10}%` : fmtHours(check.value)
}

function StatusChip({ check }: { check?: RequirementCheck }) {
  if (!check) return <span className="text-faint">no data</span>
  const Icon =
    check.status === 'met' ? CheckCircle2 : check.status === 'not_met' ? XCircle : CircleHelp
  return (
    <span
      className={cn('inline-flex items-center gap-1 whitespace-nowrap text-xs font-medium', STATUS_STYLE[check.status])}
      title={check.detail}
    >
      <Icon className="size-3.5" aria-hidden />
      {STATUS_WORD[check.status]}
    </span>
  )
}

function Verdict({ outcome }: { outcome: Outcome }) {
  if (outcome.error) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-alert" title={outcome.error}>
        <AlertTriangle className="size-3.5" aria-hidden /> not evaluated
      </span>
    )
  }
  const satisfied = outcome.evaluation?.satisfied
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-xs font-medium',
        satisfied === true ? 'text-both' : satisfied === false ? 'text-sun' : 'text-faint',
      )}
    >
      {satisfied === true ? (
        <CheckCircle2 className="size-3.5" aria-hidden />
      ) : satisfied === false ? (
        <XCircle className="size-3.5" aria-hidden />
      ) : (
        <CircleHelp className="size-3.5" aria-hidden />
      )}
      {satisfied === true ? 'meets all' : satisfied === false ? 'fails' : 'undecided'}
    </span>
  )
}

/**
 * Phase 4 Tasks 7 and 8: one shared landing window, one shared threshold set,
 * every Phase 1 candidate evaluated by the same requirement engine. The table
 * reports each measure and each pass/fail independently; it never combines
 * them into a ranking.
 */
export function CandidateComparison() {
  const { config, sites, mode, draftA } = useApp()
  const defaults = config.requirements
  const sim = config.simulation

  const candidates = React.useMemo(
    () =>
      config.mission.candidate_sites.flatMap((id) => sites.filter((site) => site.id === id)),
    [config.mission.candidate_sites, sites],
  )

  const [landing, setLanding] = React.useState(draftA.landing_utc)
  const [duration, setDuration] = React.useState(draftA.duration_hours)
  const [sun, setSun] = React.useState(String(defaults.min_sun_visible_pct))
  const [earth, setEarth] = React.useState(String(defaults.min_earth_visible_pct))
  const [blackout, setBlackout] = React.useState(String(defaults.max_earth_blackout_hours))
  const [requested, setRequested] = React.useState(false)

  const sunNum = Number(sun)
  const earthNum = Number(earth)
  const blackoutNum = Number(blackout)
  const thresholdProblem =
    sun.trim() === '' || !Number.isFinite(sunNum) || sunNum < 0 || sunNum > 100
      ? 'Minimum sunlight must be between 0 and 100%.'
      : earth.trim() === '' || !Number.isFinite(earthNum) || earthNum < 0 || earthNum > 100
        ? 'Minimum Earth visibility must be between 0 and 100%.'
        : blackout.trim() === '' || !Number.isFinite(blackoutNum) || blackoutNum < 0
          ? 'Maximum blackout must be zero or more hours.'
          : null

  const windowDraft = { ...draftA, landing_utc: landing, duration_hours: duration }
  const rangeError = rangeProblem(windowDraft, sim.supported_start_utc, sim.supported_end_utc)
  const problem = thresholdProblem ?? rangeError

  React.useEffect(() => {
    setRequested(false)
  }, [landing, duration, sun, earth, blackout, mode])

  const thresholds = {
    min_sun_visible_pct: sunNum,
    min_earth_visible_pct: earthNum,
    max_earth_blackout_hours: blackoutNum,
  }
  const key =
    requested && !problem && candidates.length > 0
      ? JSON.stringify({
          mode,
          landing,
          duration,
          thresholds,
          sites: candidates.map((site) => site.id),
        })
      : null

  const comparison = useApiResource<Outcome[]>(
    key,
    async (signal) => {
      const settled = await Promise.allSettled(
        candidates.map((site) =>
          api
            .requirements(
              { location: { site_id: site.id }, landing_utc: landing, duration_hours: duration, mode },
              thresholds,
              signal,
            )
            .then((evaluation) => ({ site, evaluation })),
        ),
      )
      if (settled.every((result) => result.status === 'rejected')) {
        throw settled[0].status === 'rejected' ? settled[0].reason : new Error('Comparison failed')
      }
      return settled.map((result, index) =>
        result.status === 'fulfilled'
          ? result.value
          : {
              site: candidates[index],
              error: result.reason instanceof Error ? result.reason.message : String(result.reason),
            },
      )
    },
    0,
  )

  const rows = comparison.data ?? []
  const bestSite = (metric: 'sun' | 'earth' | 'blackout') => {
    let bestId: string | null = null
    let bestValue: number | null = null
    for (const outcome of rows) {
      const check = checkFor(outcome.evaluation, CHECK_IDS[metric])
      if (check?.value == null) continue
      if (
        bestValue === null ||
        (metric === 'blackout' ? check.value < bestValue : check.value > bestValue)
      ) {
        bestId = outcome.site.id
        bestValue = check.value
      }
    }
    return bestId
  }

  const sunLeaderId = bestSite('sun')
  const earthLeaderId = bestSite('earth')
  const blackoutLeaderId = bestSite('blackout')
  const siteName = (id: string | null) =>
    candidates.find((site) => site.id === id)?.name ?? null
  const checkValue = (id: string, metric: 'sun' | 'earth' | 'blackout') =>
    checkFor(rows.find((outcome) => outcome.site.id === id)?.evaluation, CHECK_IDS[metric])
  const leaderText = (id: string | null, metric: 'sun' | 'earth' | 'blackout') => {
    const check = id ? checkValue(id, metric) : undefined
    return check ? fmtValue(check) : '—'
  }

  const reset = () => {
    setSun(String(defaults.min_sun_visible_pct))
    setEarth(String(defaults.min_earth_visible_pct))
    setBlackout(String(defaults.max_earth_blackout_hours))
    setRequested(false)
  }

  return (
    <Card>
      <CardHeader
        title="Compare all candidates over one window"
        description="Every Phase 1 candidate uses the same landing time, duration and thresholds. Values come from the same requirement engine as the planner; pass/fail is reported per measure, never merged into a ranking."
      />
      <CardContent className="space-y-4">
        <ScenarioEditor
          draft={windowDraft}
          onChange={(next) => {
            setLanding(next.landing_utc)
            setDuration(next.duration_hours)
          }}
          showSite={false}
        />

        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Minimum sunlight" hint="Share of the window with Sun above the skyline">
            <div className="flex items-center gap-1.5">
              <Input
                type="number"
                min={0}
                max={100}
                step={1}
                value={sun}
                aria-label="Minimum sunlight percent"
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(sunNum) || sunNum < 0 || sunNum > 100)}
                onChange={(e) => setSun(e.target.value)}
              />
              <span className="text-sm text-muted">%</span>
            </div>
          </Field>
          <Field label="Minimum Earth visibility" hint="Share of the window with Earth above the skyline">
            <div className="flex items-center gap-1.5">
              <Input
                type="number"
                min={0}
                max={100}
                step={1}
                value={earth}
                aria-label="Minimum Earth visibility percent"
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(earthNum) || earthNum < 0 || earthNum > 100)}
                onChange={(e) => setEarth(e.target.value)}
              />
              <span className="text-sm text-muted">%</span>
            </div>
          </Field>
          <Field label="Maximum Earth blackout" hint="Longest continuous Earth outage allowed">
            <div className="flex items-center gap-1.5">
              <Input
                type="number"
                min={0}
                step={1}
                value={blackout}
                aria-label="Maximum Earth blackout hours"
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(blackoutNum) || blackoutNum < 0)}
                onChange={(e) => setBlackout(e.target.value)}
              />
              <span className="shrink-0 text-sm text-muted">h</span>
            </div>
          </Field>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setRequested(true)} disabled={problem !== null || comparison.loading}>
            {comparison.loading ? 'Comparing…' : 'Compare all candidates'}
          </Button>
          <Button variant="ghost" size="sm" onClick={reset}>
            Phase 1 targets
          </Button>
          <p className="text-xs text-muted">
            {fmtUtc(landing)} UTC for {fmtHours(duration)}. Demonstration targets only — not NASA flight requirements.
          </p>
        </div>
        {problem && <p className="text-xs text-alert">{problem}</p>}
        {comparison.error && <ErrorNotice error={comparison.error} />}

        {rows.length > 0 && !comparison.error && (
          <div
            className={cn('space-y-3', comparison.loading && 'opacity-70')}
            role="region"
            aria-live="polite"
            aria-label="All-candidate comparison results"
          >
            <div className="space-y-2 sm:hidden">
              {rows.map((outcome) => {
                const sunCheck = checkFor(outcome.evaluation, CHECK_IDS.sun)
                const earthCheck = checkFor(outcome.evaluation, CHECK_IDS.earth)
                const blackoutCheck = checkFor(outcome.evaluation, CHECK_IDS.blackout)
                return (
                  <div key={outcome.site.id} className="rounded-md border border-rule-soft p-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-ink">{outcome.site.name}</p>
                      <Verdict outcome={outcome} />
                    </div>
                    <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <dt className="text-faint">Sun visible</dt>
                        <dd className="num text-ink">{fmtValue(sunCheck)}</dd>
                        <dd><StatusChip check={sunCheck} /></dd>
                      </div>
                      <div>
                        <dt className="text-faint">Earth visible</dt>
                        <dd className="num text-ink">{fmtValue(earthCheck)}</dd>
                        <dd><StatusChip check={earthCheck} /></dd>
                      </div>
                      <div>
                        <dt className="text-faint">Earth blackout</dt>
                        <dd className="num text-ink">{fmtValue(blackoutCheck)}</dd>
                        <dd><StatusChip check={blackoutCheck} /></dd>
                      </div>
                    </dl>
                  </div>
                )
              })}
            </div>
            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full min-w-[820px] text-left text-xs">
                <thead>
                  <tr className="text-faint">
                    <th className="px-2 py-1.5 font-medium">Candidate</th>
                    <th className="px-2 py-1.5 text-right font-medium" title="Share of the window with the Sun above the skyline">Sun visible</th>
                    <th className="px-2 py-1.5 text-right font-medium" title="Share of the window with Earth above the skyline">Earth visible</th>
                    <th className="px-2 py-1.5 text-right font-medium" title="Longest continuous Earth outage">Longest Earth blackout</th>
                    <th className="px-2 py-1.5 font-medium">Sun target</th>
                    <th className="px-2 py-1.5 font-medium">Earth target</th>
                    <th className="px-2 py-1.5 font-medium">Blackout target</th>
                    <th className="px-2 py-1.5 font-medium">Overall</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((outcome) => {
                    const sunCheck = checkFor(outcome.evaluation, CHECK_IDS.sun)
                    const earthCheck = checkFor(outcome.evaluation, CHECK_IDS.earth)
                    const blackoutCheck = checkFor(outcome.evaluation, CHECK_IDS.blackout)
                    const best = (id: string | null, check?: RequirementCheck) =>
                      check?.value != null && id === outcome.site.id
                    return (
                      <tr key={outcome.site.id}>
                        <td className="border-t border-rule-soft px-2 py-2 text-ink">{outcome.site.name}</td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {fmtValue(sunCheck)}
                          {best(sunLeaderId, sunCheck) && <span className="ml-1.5 rounded bg-both/15 px-1 py-0.5 text-[10px] text-both">highest</span>}
                        </td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {fmtValue(earthCheck)}
                          {best(earthLeaderId, earthCheck) && <span className="ml-1.5 rounded bg-both/15 px-1 py-0.5 text-[10px] text-both">highest</span>}
                        </td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {fmtValue(blackoutCheck)}
                          {best(blackoutLeaderId, blackoutCheck) && <span className="ml-1.5 rounded bg-both/15 px-1 py-0.5 text-[10px] text-both">shortest</span>}
                        </td>
                        <td className="border-t border-rule-soft px-2 py-2"><StatusChip check={sunCheck} /></td>
                        <td className="border-t border-rule-soft px-2 py-2"><StatusChip check={earthCheck} /></td>
                        <td className="border-t border-rule-soft px-2 py-2"><StatusChip check={blackoutCheck} /></td>
                        <td className="border-t border-rule-soft px-2 py-2"><Verdict outcome={outcome} /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="space-y-1 rounded-md border border-rule-soft p-3 text-xs text-muted">
              <p>
                Most sunlight: <span className="text-ink">{siteName(sunLeaderId) ?? '—'}</span> ({leaderText(sunLeaderId, 'sun')}).
                Most Earth visibility: <span className="text-ink">{siteName(earthLeaderId) ?? '—'}</span> ({leaderText(earthLeaderId, 'earth')}).
                Shortest Earth blackout: <span className="text-ink">{siteName(blackoutLeaderId) ?? '—'}</span> ({leaderText(blackoutLeaderId, 'blackout')}).
              </p>
              <p>
                Different measures can point to different sites. The table does not combine them into a score:
                if power is the binding constraint, the most-sunlight site is the relevant comparison; if
                communications continuity matters most, the shortest-blackout site is. A stronger sunlight
                result does not automatically make a site preferable.
              </p>
            </div>

            <p className="text-xs text-faint">
              Model: {mode === 'demo' ? 'demo ephemeris and synthetic skylines' : mode === 'jpl' ? 'JPL Horizons geometry, LOLA terrain where a mask exists' : 'stored JPL Horizons series and LOLA skylines'}.
              Terrain-adjusted and geometric results are not averaged. Sunlight is not available power; Earth
              visibility is not a working communications link.{' '}
              <a className="text-signal underline-offset-2 hover:underline" href="#methodology">Data &amp; methodology</a>.
            </p>
            {rows.some((outcome) => outcome.error) && (
              <p className="text-xs text-alert">
                Some candidates could not be evaluated; their row says “not evaluated” rather than showing an assumed value.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
