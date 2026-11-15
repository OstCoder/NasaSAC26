import { CalendarClock, GitCompare, LoaderCircle } from 'lucide-react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { ProvenanceBadge } from '@/components/ProvenanceBadge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScenarioEditor, rangeProblem } from '@/features/mission-planner/ScenarioEditor'
import { FeasibilityPanel } from '@/features/phase3/FeasibilityPanel'
import { CandidateComparison } from './CandidateComparison'
import { ReschedulerPanel } from '@/features/rescheduler'
import { useApiResource } from '@/hooks/useApiResource'
import { useApp } from '@/hooks/useAppContext'
import { draftToInput } from '@/hooks/useScenario'
import { fmtHours, fmtUtc } from '@/lib/format'
import { api } from '@/services/api'
import type { ComparisonResult, ScenarioResult } from '@/types/api'
import { DeltaTable } from './DeltaTable'
import { PairedBands } from './PairedBands'
import { TradeoffNotes } from './TradeoffNotes'

function ScenarioHeading({ r, tag, color }: { r: ScenarioResult; tag: string; color: string }) {
  return (
    <div className="min-w-0">
      <p className="font-display text-base font-semibold">
        <span style={{ color }}>{tag}</span> {r.location.name}
      </p>
      <p className="num text-xs text-muted">
        {fmtUtc(r.landing_utc)} UTC, {fmtHours(r.duration_hours)}
      </p>
      <ProvenanceBadge level={r.provenance.overall} className="mt-1.5" />
    </div>
  )
}

function TwoScenarios() {
  const { draftA, setDraftA, draftB, setDraftB, mode, config } = useApp()
  const sim = config.simulation
  const a = draftToInput(draftA, mode, 'A')
  const b = draftToInput(draftB, mode, 'B')
  const blocked =
    rangeProblem(draftA, sim.supported_start_utc, sim.supported_end_utc) ||
    rangeProblem(draftB, sim.supported_start_utc, sim.supported_end_utc)
  const cmp = useApiResource<ComparisonResult>(blocked ? null : JSON.stringify([a, b]), () => api.compare(a, b), 350)

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {([['A', draftA, setDraftA, '#6b9cff'], ['B', draftB, setDraftB, '#c79bff']] as const).map(([tag, d, set, color]) => (
          <Card key={tag} style={{ borderTop: `2px solid ${color}` }}>
            <CardHeader title={`Scenario ${tag}`} />
            <CardContent>
              <ScenarioEditor draft={d} onChange={set} />
            </CardContent>
          </Card>
        ))}
      </div>

      {cmp.error && <ErrorNotice error={cmp.error} onRetry={cmp.retry} />}
      {cmp.loading && !cmp.data && (
        <p className="flex items-center gap-2 text-sm text-muted"><LoaderCircle className="size-4 animate-spin" /> Comparing…</p>
      )}

      {cmp.data && !cmp.error && (
        <Card className={cmp.loading ? 'opacity-70 transition-opacity' : ''}>
          <CardHeader title="Side by side" description="Same calculation, two inputs. Hover a measure for a plain-language statement." />
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4 border-b border-rule-soft pb-4">
              <ScenarioHeading r={cmp.data.a} tag="A" color="#6b9cff" />
              <ScenarioHeading r={cmp.data.b} tag="B" color="#c79bff" />
            </div>
            <DeltaTable deltas={cmp.data.deltas} />
            <div>
              <h3 className="mb-2 font-display text-sm font-semibold text-muted">Visibility since landing</h3>
              <PairedBands a={cmp.data.a} b={cmp.data.b} aLabel={`A: ${cmp.data.a.location.name}`} bLabel={`B: ${cmp.data.b.location.name}`} />
            </div>
            <TradeoffNotes result={cmp.data} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export function ComparisonPage() {
  const { features } = useApp()
  return (
    <Tabs defaultValue="pair" className="space-y-4">
      <TabsList aria-label="Comparison type">
        <TabsTrigger value="pair"><GitCompare /> Two scenarios</TabsTrigger>
        <TabsTrigger value="candidates">All candidates</TabsTrigger>
        {features.rescheduler && <TabsTrigger value="reschedule"><CalendarClock /> Reschedule a mission</TabsTrigger>}
      </TabsList>
      <TabsContent value="pair"><TwoScenarios /></TabsContent>
      <TabsContent value="candidates">
        <div className="space-y-4">
          <CandidateComparison />
          <FeasibilityPanel />
        </div>
      </TabsContent>
      {features.rescheduler && <TabsContent value="reschedule"><ReschedulerPanel /></TabsContent>}
    </Tabs>
  )
}
