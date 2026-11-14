import { ErrorNotice } from '@/components/ErrorNotice'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { useFeasibilityMatrix } from '@/hooks/useScenario'
import { cn } from '@/lib/utils'
import type { FeasibilityRow, RequirementCheck, RequirementStatus } from '@/types/api'

const pct = (value: number | null | undefined) => (value == null ? '—' : `${Math.round(value)}%`)

const STATUS_STYLE: Record<RequirementStatus, string> = {
  met: 'text-both',
  not_met: 'text-sun',
  unknown: 'text-faint',
}
const STATUS_WORD: Record<RequirementStatus, string> = {
  met: 'met',
  not_met: 'not met',
  unknown: 'unknown',
}

function StatusCell({ check }: { check: RequirementCheck }) {
  return (
    <td className="border-t border-rule-soft px-2 py-1.5 text-center" title={check.detail}>
      <span className={cn('num text-xs font-medium', STATUS_STYLE[check.status])}>
        {STATUS_WORD[check.status]}
      </span>
      <span className="block text-[10px] text-faint">
        {pct(check.value)} / {check.comparison === 'at_least' ? '≥' : '≤'} {check.threshold}
      </span>
    </td>
  )
}

function VerdictCell({ satisfied }: { satisfied: boolean | null }) {
  return (
    <td className="border-t border-rule-soft px-2 py-1.5 text-center">
      <span
        className={cn(
          'text-xs font-medium',
          satisfied === true ? 'text-both' : satisfied === false ? 'text-sun' : 'text-faint',
        )}
      >
        {satisfied === true ? 'meets all' : satisfied === false ? 'fails' : 'undecided'}
      </span>
    </td>
  )
}

function BasisCell({ row }: { row: FeasibilityRow }) {
  const terrain = row.summary
  const geo = row.geometric_baseline
  if (!terrain) return <span className="text-xs text-faint">—</span>
  return (
    <div className="text-xs">
      <span className="num text-ink" title="Body centre above the LOLA skyline">
        {pct(terrain.sun_visible_pct)} Sun · {pct(terrain.earth_visible_pct)} Earth (terrain)
      </span>
      {geo && (
        <span className="num block text-faint" title="Flat 0° horizon, Task 1/Task 2 rule">
          {pct(geo.sun.visible_sample_pct)} Sun · {pct(geo.earth.visible_sample_pct)} Earth (geometric)
        </span>
      )}
    </div>
  )
}

/**
 * Phase 4: the feasibility matrix. Every Phase 1 candidate x both mission
 * windows, each checked against the shared requirement thresholds —
 * pass/fail/unknown per requirement, verdicts never merged into a ranking.
 * Terrain and geometric numbers are shown side by side, never averaged.
 */
export function FeasibilityPanel() {
  const matrix = useFeasibilityMatrix()
  const thresholds = matrix.data?.thresholds
  const rows = matrix.data?.rows ?? []
  const pending = !matrix.data && !matrix.error

  return (
    <Card>
      <CardHeader
        title="Feasibility matrix"
        description={
          thresholds
            ? `Phase 1 targets: ≥ ${thresholds.min_sun_visible_pct}% Sun, ≥ ${thresholds.min_earth_visible_pct}% Earth, ≤ ${thresholds.max_earth_blackout_hours} h blackout — per candidate and window`
            : 'Loading Phase 1 targets…'
        }
      />
      <CardContent>
        {matrix.error && <ErrorNotice error={matrix.error} />}
        {pending && <p className="text-xs text-faint">Loading the matrix…</p>}
        {rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-faint">
                  <th className="px-2 py-1.5 font-medium">Candidate · window</th>
                  <th className="px-2 py-1.5 text-center font-medium" title="Minimum sunlight availability">
                    Sun % ≥ {thresholds?.min_sun_visible_pct}
                  </th>
                  <th className="px-2 py-1.5 text-center font-medium" title="Minimum Earth visibility">
                    Earth % ≥ {thresholds?.min_earth_visible_pct}
                  </th>
                  <th className="px-2 py-1.5 text-center font-medium" title="Longest Earth blackout">
                    Blackout ≤ {thresholds?.max_earth_blackout_hours} h
                  </th>
                  <th className="px-2 py-1.5 text-center font-medium">Verdict</th>
                  <th className="px-2 py-1.5 font-medium">Terrain vs geometric</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => {
                  const checks = new Map(row.checks.map((check) => [check.id, check]))
                  const windowLabel = row.window.label ?? row.window.key
                  return (
                    <tr key={`${row.site_id}:${row.window.key}:${index}`}>
                      <td className="border-t border-rule-soft px-2 py-1.5">
                        <span className="text-ink">{row.name ?? row.site_id}</span>
                        <span className="block text-faint">{windowLabel}</span>
                      </td>
                      {row.available === false ? (
                        <td colSpan={5} className="border-t border-rule-soft px-2 py-1.5 text-faint">
                          {row.reason ?? 'not available'}
                        </td>
                      ) : (
                        <>
                          <StatusCell check={checks.get('min_sun_visible_pct')!} />
                          <StatusCell check={checks.get('min_earth_visible_pct')!} />
                          <StatusCell check={checks.get('max_earth_blackout_hours')!} />
                          <VerdictCell satisfied={row.satisfied} />
                        </>
                      )}
                      <td className="border-t border-rule-soft px-2 py-1.5">
                        <BasisCell row={row} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        {matrix.data?.notes && (
          <ul className="mt-3 space-y-1 text-xs text-faint">
            {matrix.data.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
