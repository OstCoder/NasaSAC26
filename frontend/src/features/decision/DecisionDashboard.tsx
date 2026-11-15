import {
  AlertTriangle,
  Award,
  CheckCircle2,
  CircleHelp,
  Compass,
  RotateCcw,
  XCircle,
} from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Field, Input } from '@/components/ui/field'
import { ScenarioEditor, rangeProblem } from '@/features/mission-planner/ScenarioEditor'
import { useApp } from '@/hooks/useAppContext'
import { useDecision } from '@/hooks/useScenario'
import { fmtHours, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type {
  DecisionPower,
  DecisionResult,
  DecisionSite,
  DecisionWeights,
  RequirementStatus,
} from '@/types/api'

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

const PRIORITIES: {
  id: string
  label: string
  hint: string
  weights: DecisionWeights
}[] = [
  {
    id: 'balanced',
    label: 'Balanced',
    hint: 'Sunlight, Earth visibility and blackout continuity carry similar weight.',
    weights: { sunlight: 0.4, earth_visibility: 0.3, communication: 0.2, science: 0 },
  },
  {
    id: 'sunlight',
    label: 'Sunlight first',
    hint: 'Favours the most Sun above the skyline, with Earth visibility as a secondary check.',
    weights: { sunlight: 0.7, earth_visibility: 0.15, communication: 0.15, science: 0 },
  },
  {
    id: 'communication',
    label: 'Communications first',
    hint: 'Favours short Earth blackouts and Earth visibility over raw sunlight.',
    weights: { sunlight: 0.15, earth_visibility: 0.25, communication: 0.6, science: 0 },
  },
  {
    id: 'science',
    label: 'Science exploration',
    hint: 'Science exploration mode prioritises mapped PSR proximity while keeping every operational check visible. Closer is not proof of water ice or rover access.',
    weights: { sunlight: 0.3, earth_visibility: 0.2, communication: 0.1, science: 0.4 },
  },
]

const pct = (value: number | null | undefined) =>
  value == null ? '—' : `${(Math.round(value * 10) / 10).toFixed(1)}%`
const hours = (value: number | null | undefined) => (value == null ? '—' : fmtHours(value))

function StatusChip({ status }: { status: RequirementStatus }) {
  const Icon =
    status === 'met' ? CheckCircle2 : status === 'not_met' ? XCircle : CircleHelp
  return (
    <span className={cn('inline-flex items-center gap-1 whitespace-nowrap text-xs font-medium', STATUS_STYLE[status])}>
      <Icon className="size-3.5" aria-hidden />
      {STATUS_WORD[status]}
    </span>
  )
}

function SiteStatus({ site }: { site: DecisionSite }) {
  return <StatusChip status={site.status === 'pass' ? 'met' : site.status === 'fail' ? 'not_met' : 'unknown'} />
}

function PowerCell({ power }: { power: DecisionPower }) {
  if (!power.available || !power.battery) {
    return <span className="text-xs text-faint">undecided</span>
  }
  return (
    <span className={cn('text-xs', power.battery.reserve_respected ? 'text-both' : 'text-sun')}>
      min {power.battery.min_soc_pct.toFixed(1)}%
      {power.battery.unserved_wh > 0 && ` · ${Math.round(power.battery.unserved_wh)} Wh unserved`}
    </span>
  )
}

function ScoreBar({ site }: { site: DecisionSite }) {
  if (site.score == null) return <span className="text-xs text-faint">not ranked</span>
  return (
    <div className="min-w-[92px]">
      <div className="flex items-baseline justify-between gap-2">
        <span className="num text-sm font-semibold text-ink">{site.score.toFixed(1)}</span>
        <span className="text-[10px] text-faint">/100</span>
      </div>
      <div className="mt-1 h-1 rounded bg-rule-soft" aria-hidden>
        <div className="h-1 rounded bg-signal" style={{ width: `${Math.max(0, Math.min(100, site.score))}%` }} />
      </div>
    </div>
  )
}

function SiteDetails({ site }: { site: DecisionSite }) {
  return (
    <div className="rounded-md border border-rule-soft p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-display text-sm font-semibold text-ink">
            {site.rank != null && (
              <span className="mr-1.5 rounded bg-signal/15 px-1.5 py-0.5 text-[11px] text-signal">
                #{site.rank}
              </span>
            )}
            {site.name}
          </p>
          <p className="text-xs text-faint">
            {site.provenance.replace(/_/g, ' ')}
            {site.nearest_psr
              ? ` · nearest mapped PSR ${site.nearest_psr.distance_km.toFixed(1)} km (${site.nearest_psr.label})`
              : ' · no mapped PSR proximity'}
          </p>
        </div>
        <SiteStatus site={site} />
      </div>

      <ul className="mt-2 space-y-1 text-xs text-muted">
        {site.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>

      {site.risks.length > 0 && (
        <div className="mt-2 rounded border border-sun/25 bg-sun/5 p-2">
          <p className="flex items-center gap-1 text-[11px] font-medium text-sun">
            <AlertTriangle className="size-3.5" aria-hidden /> Risks and undecided evidence
          </p>
          <ul className="mt-1 space-y-1 text-xs text-muted">
            {site.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
        </div>
      )}

      {site.score != null && Object.keys(site.score_components).length > 0 && (
        <p className="mt-2 text-[11px] text-faint">
          Score components (0–1):{' '}
          {Object.entries(site.score_components)
            .map(([key, value]) => `${key.replace(/_/g, ' ')} ${value.toFixed(2)}`)
            .join(' · ')}
        </p>
      )}

      {site.power.available && site.power.battery ? (
        <p className="mt-2 text-xs text-faint">
          Power model: {site.power.load_w?.toFixed(0)} W load, {Math.round(site.power.array_energy_wh ?? 0)} Wh
          array energy, battery minimum {site.power.battery.min_soc_pct.toFixed(1)}% (reserve{' '}
          {site.power.battery.reserve_pct.toFixed(0)}%). {site.power.battery.verdict}
        </p>
      ) : (
        <p className="mt-2 text-xs text-faint">{site.power.reason}</p>
      )}
    </div>
  )
}

/**
 * Phase 5 Tasks 7-11: a live decision dashboard. Requirements are sent to one
 * backend evaluator, which applies the shared scenario metrics, maximum
 * darkness and the Phase 5 power model. Only candidates that pass every
 * selected constraint are ranked; undecided and failed sites remain visible
 * but never receive a favourable score.
 */
export function DecisionDashboard() {
  const { config, sites, mode, draftA } = useApp()
  const defaults = config.requirements
  const sim = config.simulation
  const candidates = React.useMemo(
    () => config.mission.candidate_sites.flatMap((id) => sites.filter((site) => site.id === id)),
    [config.mission.candidate_sites, sites],
  )

  const [landing, setLanding] = React.useState(draftA.landing_utc)
  const [duration, setDuration] = React.useState(draftA.duration_hours)
  const [sun, setSun] = React.useState(String(defaults.min_sun_visible_pct))
  const [earth, setEarth] = React.useState(String(defaults.min_earth_visible_pct))
  const [blackout, setBlackout] = React.useState(String(defaults.max_earth_blackout_hours))
  const [darkness, setDarkness] = React.useState(String(defaults.max_darkness_hours ?? 16))
  const [power, setPower] = React.useState(String(defaults.power_demand_w ?? 40))
  // The committed windows censor every longest-blackout measurement, so an
  // "at most" check can never be PASS here. Keep it visible and advisory by
  // default instead of making the dashboard unable to rank any site.
  const [requireBlackout, setRequireBlackout] = React.useState(false)
  const [priorityId, setPriorityId] = React.useState('balanced')

  const sunNum = Number(sun)
  const earthNum = Number(earth)
  const blackoutNum = Number(blackout)
  const darknessNum = Number(darkness)
  const powerNum = Number(power)
  const priority = PRIORITIES.find((item) => item.id === priorityId) ?? PRIORITIES[0]
  const thresholdProblem =
    sun.trim() === '' || !Number.isFinite(sunNum) || sunNum < 0 || sunNum > 100
      ? 'Minimum sunlight must be between 0 and 100%.'
      : earth.trim() === '' || !Number.isFinite(earthNum) || earthNum < 0 || earthNum > 100
        ? 'Minimum Earth visibility must be between 0 and 100%.'
        : blackout.trim() === '' || !Number.isFinite(blackoutNum) || blackoutNum < 0
          ? 'Maximum Earth blackout must be zero or more hours.'
          : darkness.trim() === '' || !Number.isFinite(darknessNum) || darknessNum < 0
            ? 'Maximum darkness must be zero or more hours.'
            : power.trim() === '' || !Number.isFinite(powerNum) || powerNum < 0 || powerNum > 100_000
              ? 'Average power demand must be between 0 and 100,000 W.'
              : null

  const windowDraft = { ...draftA, landing_utc: landing, duration_hours: duration }
  const problem = thresholdProblem ?? rangeProblem(windowDraft, sim.supported_start_utc, sim.supported_end_utc)
  const body =
    problem === null && candidates.length > 0
      ? {
          landing_utc: landing,
          duration_hours: duration,
          mode,
          site_ids: candidates.map((site) => site.id),
          thresholds: {
            min_sun_visible_pct: sunNum,
            min_earth_visible_pct: earthNum,
            max_earth_blackout_hours: blackoutNum,
            max_darkness_hours: darknessNum,
            power_demand_w: powerNum,
          },
          weights: priority.weights,
          optional_checks: requireBlackout ? [] : ['max_earth_blackout_hours'],
        }
      : null
  const requestKey = body ? JSON.stringify(body) : null
  const decision = useDecision(body)

  const reset = () => {
    setSun(String(defaults.min_sun_visible_pct))
    setEarth(String(defaults.min_earth_visible_pct))
    setBlackout(String(defaults.max_earth_blackout_hours))
    setDarkness(String(defaults.max_darkness_hours ?? 16))
    setPower(String(defaults.power_demand_w ?? 40))
    setRequireBlackout(false)
    setPriorityId('balanced')
  }

  // Never show the previous ranking under newly edited inputs while the next
  // evaluation is debounced or in flight.
  const result: DecisionResult | null =
    decision.dataKey === requestKey ? decision.data : null
  const orderedSites = React.useMemo(() => {
    if (!result) return []
    return [...result.sites].sort((a, b) => {
      if (a.rank != null && b.rank != null) return a.rank - b.rank
      if (a.rank != null) return -1
      if (b.rank != null) return 1
      return 0
    })
  }, [result])
  const top = result?.sites.find((site) => site.site_id === result.recommendation.top_site_id)
  const windows = new Set(result?.sites.map((site) => site.power.window).filter(Boolean) ?? [])

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Mission decision support"
          description="Set the mission window and operational constraints. The same evaluator checks every candidate, then ranks only the sites that pass all selected checks. Demonstration targets and weights — not NASA flight requirements."
          actions={
            <Button size="sm" variant="ghost" onClick={reset}>
              <RotateCcw /> Defaults
            </Button>
          }
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

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Field label="Minimum sunlight (%)" hint="Sun above the skyline">
              <Input
                type="number"
                min={0}
                max={100}
                step={1}
                value={sun}
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(sunNum) || sunNum < 0 || sunNum > 100)}
                onChange={(e) => setSun(e.target.value)}
              />
            </Field>
            <Field label="Minimum Earth visibility (%)" hint="Earth above the skyline">
              <Input
                type="number"
                min={0}
                max={100}
                step={1}
                value={earth}
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(earthNum) || earthNum < 0 || earthNum > 100)}
                onChange={(e) => setEarth(e.target.value)}
              />
            </Field>
            <Field label="Maximum Earth blackout (h)" hint="Longest Earth outage allowed">
              <Input
                type="number"
                min={0}
                step={1}
                value={blackout}
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(blackoutNum) || blackoutNum < 0)}
                onChange={(e) => setBlackout(e.target.value)}
              />
              <label className="flex items-start gap-1.5 text-[11px] leading-snug text-muted">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={requireBlackout}
                  onChange={(e) => setRequireBlackout(e.target.checked)}
                />
                Require for eligibility
              </label>
            </Field>
            <Field label="Maximum darkness (h)" hint="Longest Sun outage allowed">
              <Input
                type="number"
                min={0}
                step={1}
                value={darkness}
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(darknessNum) || darknessNum < 0)}
                onChange={(e) => setDarkness(e.target.value)}
              />
            </Field>
            <Field label="Average power demand (W)" hint="Used by the battery model">
              <Input
                type="number"
                min={0}
                step={1}
                value={power}
                aria-invalid={thresholdProblem !== null && (!Number.isFinite(powerNum) || powerNum < 0 || powerNum > 100_000)}
                onChange={(e) => setPower(e.target.value)}
              />
            </Field>
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1.5 text-[13px] text-muted">
                <Compass className="size-4" aria-hidden /> Priority
              </span>
              {PRIORITIES.map((item) => (
                <Button
                  key={item.id}
                  size="sm"
                  variant={item.id === priorityId ? 'secondary' : 'ghost'}
                  aria-pressed={item.id === priorityId}
                  onClick={() => setPriorityId(item.id)}
                >
                  {item.label}
                </Button>
              ))}
            </div>
            <p className="text-xs text-faint">
              {priority.hint} Weights: sunlight {priority.weights.sunlight.toFixed(2)}, Earth visibility{' '}
              {priority.weights.earth_visibility.toFixed(2)}, communication{' '}
              {priority.weights.communication.toFixed(2)}, science {priority.weights.science.toFixed(2)}.
              They are normalised over the eligible candidates; they are not a NASA suitability score.
            </p>
          </div>

          {problem && <p className="text-xs text-alert">{problem}</p>}
          {decision.error && <ErrorNotice error={decision.error} onRetry={decision.retry} />}
          <p className="text-xs text-faint" aria-live="polite">
            {decision.loading ? 'Re-evaluating all candidates…' : 'Results update automatically when a constraint or the mission window changes.'}
          </p>
          <p className="text-xs text-faint">
            Earth blackout is advisory by default because every committed window censors the measured
            interval: an “at most” check can only be UNDECIDED, never PASS. Requiring it keeps the
            measurement visible but makes these committed windows ineligible; it is never silently
            treated as passed.
          </p>
        </CardContent>
      </Card>

      {result && !decision.error && (
        <div className={cn('space-y-4', decision.loading && 'opacity-70 transition-opacity')} aria-live="polite">
          <Card>
            <CardHeader
              title={result.recommendation.status === 'ranked' ? 'Recommendation' : 'No eligible candidate'}
              description={`${fmtUtc(result.landing_utc)} UTC for ${fmtHours(result.duration_hours)} · ${result.mode} mode`}
            />
            <CardContent className="space-y-3">
              <div
                className={cn(
                  'flex items-start gap-3 rounded-md border p-3',
                  result.recommendation.status === 'ranked'
                    ? 'border-both/40 bg-both/5'
                    : 'border-sun/40 bg-sun/5',
                )}
              >
                {result.recommendation.status === 'ranked' ? (
                  <Award className="mt-0.5 size-5 shrink-0 text-both" aria-hidden />
                ) : (
                  <AlertTriangle className="mt-0.5 size-5 shrink-0 text-sun" aria-hidden />
                )}
                <div>
                  <p className="font-display text-base font-semibold text-ink">
                    {result.recommendation.top_site_name
                      ? `${result.recommendation.top_site_name} is top-ranked`
                      : 'No site is recommended'}
                    {result.mode === 'demo' && (
                      <span className="ml-2 rounded border border-sun/50 bg-sun/10 px-1.5 py-0.5 text-[10px] font-normal text-sun">
                        demo model
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-sm text-muted">{result.recommendation.summary}</p>
                  {result.mode === 'demo' && (
                    <p className="mt-1 text-xs text-sun">
                      Demo Mode uses synthetic ephemeris/terrain values. This rank describes the demonstration model,
                      not verified lunar conditions.
                    </p>
                  )}
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px] text-left text-xs">
                  <thead>
                    <tr className="text-faint">
                      <th className="px-2 py-1.5 font-medium">Rank</th>
                      <th className="px-2 py-1.5 font-medium">Candidate</th>
                      <th className="px-2 py-1.5 font-medium">Status</th>
                      <th className="px-2 py-1.5 font-medium">Score</th>
                      <th className="px-2 py-1.5 text-right font-medium">Sun</th>
                      <th className="px-2 py-1.5 text-right font-medium">Earth</th>
                      <th className="px-2 py-1.5 text-right font-medium">Earth blackout</th>
                      <th className="px-2 py-1.5 text-right font-medium">Darkness</th>
                      <th className="px-2 py-1.5 font-medium">Power / battery</th>
                      <th className="px-2 py-1.5 text-right font-medium">PSR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orderedSites.map((site) => (
                      <tr key={site.site_id}>
                        <td className="num border-t border-rule-soft px-2 py-2 text-ink">
                          {site.rank ?? '—'}
                        </td>
                        <td className="border-t border-rule-soft px-2 py-2 text-ink">{site.name}</td>
                        <td className="border-t border-rule-soft px-2 py-2"><SiteStatus site={site} /></td>
                        <td className="border-t border-rule-soft px-2 py-2"><ScoreBar site={site} /></td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {pct(site.metrics.sun_visible_pct)}
                        </td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {pct(site.metrics.earth_visible_pct)}
                        </td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {hours(site.metrics.longest_earth_blackout_hours)}
                        </td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {hours(site.metrics.longest_sun_blackout_hours)}
                        </td>
                        <td className="border-t border-rule-soft px-2 py-2"><PowerCell power={site.power} /></td>
                        <td className="num border-t border-rule-soft px-2 py-2 text-right text-ink">
                          {site.nearest_psr ? `${site.nearest_psr.distance_km.toFixed(1)} km` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="grid gap-3 sm:hidden">
                {orderedSites.map((site) => (
                  <div key={`mobile-${site.site_id}`} className="rounded-md border border-rule-soft p-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-ink">
                        {site.rank != null && `#${site.rank} `}{site.name}
                      </p>
                      <SiteStatus site={site} />
                    </div>
                    <p className="num mt-1 text-xs text-muted">
                      {pct(site.metrics.sun_visible_pct)} Sun · {pct(site.metrics.earth_visible_pct)} Earth ·{' '}
                      {hours(site.metrics.longest_earth_blackout_hours)} Earth blackout ·{' '}
                      {hours(site.metrics.longest_sun_blackout_hours)} darkness
                    </p>
                    <p className="mt-1 text-xs text-faint">Score: {site.score == null ? 'not ranked' : `${site.score.toFixed(1)}/100`}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                {orderedSites.map((site) => (
                  <SiteDetails key={`details-${site.site_id}`} site={site} />
                ))}
              </div>

              <p className="text-xs text-faint">
                Ranked only from measured model values. The score is a weighted comparison, not a landing-safety
                clearance. {result.sites.some((site) => site.status === 'unknown') &&
                  'At least one site has an undecided check; undecided is not a pass. '}
                A PSR distance is straight-line proximity, not proof of water ice or rover access.
              </p>

              <div className="flex flex-wrap items-center gap-3 text-xs">
                {top?.power.window && (
                  <a
                    className="text-earth underline underline-offset-2"
                    href={api.missionReportUrl({ siteId: top.site_id, window: top.power.window })}
                    download={`lunanav-${top.site_id}-${top.power.window}.md`}
                  >
                    Download the top site mission report (.md)
                  </a>
                )}
                <a className="text-signal underline underline-offset-2" href="#compare">
                  Open detailed candidate comparison
                </a>
                <span className="text-faint">
                  {windows.size > 0
                    ? 'Power/battery is available for the committed mission window selected above.'
                    : 'Pick 1 Dec or 11 Dec 2026 UTC to include the committed power/battery model.'}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader
              title="Checks behind this recommendation"
              description="Every check uses the same measured scenario values. The reasons below are deterministic and contain no generated measurements."
            />
            <CardContent className="space-y-3">
              {orderedSites.map((site) => (
                <div key={`checks-${site.site_id}`} className="overflow-x-auto">
                  <p className="mb-1 text-xs font-medium text-ink">
                    {site.name}{' '}
                    <span className="text-faint">
                      {site.satisfied === true ? 'meets all selected constraints' : site.satisfied === false ? 'fails at least one constraint' : 'has an undecided constraint'}
                    </span>
                  </p>
                  <table className="w-full min-w-[660px] text-left text-xs">
                    <thead>
                      <tr className="text-faint">
                        <th className="px-2 py-1 font-medium">Requirement</th>
                        <th className="px-2 py-1 font-medium">Measured</th>
                        <th className="px-2 py-1 font-medium">Target</th>
                        <th className="px-2 py-1 font-medium">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {site.checks.map((check) => (
                        <tr key={`${site.site_id}-${check.id}`}>
                          <td className="border-t border-rule-soft px-2 py-1.5 text-ink">{check.label}</td>
                          <td className="num border-t border-rule-soft px-2 py-1.5">
                            {check.value == null ? '—' : check.unit === '%' ? pct(check.value) : `${check.value.toFixed(1)} ${check.unit}`}
                          </td>
                          <td className="num border-t border-rule-soft px-2 py-1.5">
                            {check.comparison === 'at_least' ? '≥' : '≤'}{' '}
                            {check.unit === '%' ? `${check.threshold}%` : `${check.threshold.toFixed(1)} ${check.unit}`}
                          </td>
                          <td className="border-t border-rule-soft px-2 py-1.5">
                            <StatusChip status={check.status} />
                            {check.required === false && (
                              <span className="ml-1.5 text-[10px] text-faint">advisory</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </CardContent>
          </Card>

          {result.weights.science > 0 && (
            <Card>
              <CardHeader
                title="Science exploration mode"
                description="Science proximity is a ranking preference, not an extra eligibility rule. Every operational check above still applies."
              />
              <CardContent className="space-y-3">
                <p className="text-xs text-muted">
                  Science weight {result.weights.science.toFixed(2)}. A closer mapped PSR raises the
                  science component, but it does not prove water ice, a traversable route, or a safe
                  landing. The operational constraints remain the gate on eligibility.
                </p>
                <ul className="space-y-2">
                  {orderedSites.map((site) => (
                    <li key={`science-${site.site_id}`} className="rounded border border-rule-soft p-2 text-xs">
                      <span className="font-medium text-ink">{site.name}</span>{' '}
                      {site.nearest_psr ? (
                        <>
                          — nearest mapped PSR <span className="num text-earth">{site.nearest_psr.distance_km.toFixed(1)} km</span>{' '}
                          ({site.nearest_psr.label}); {site.psrs_within_10_km ?? 0} mapped PSR(s) within 10 km.
                        </>
                      ) : (
                        <span className="text-faint">— no mapped PSR proximity; science component is the least favourable value.</span>
                      )}
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-faint">
                  This is a comparison context, not a traverse plan. It does not model slope, trafficability,
                  illumination along a route, or the scientific value of a specific PSR.
                </p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader title="Model limits" />
            <CardContent>
              <ul className="space-y-1 text-xs text-faint">
                {result.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
