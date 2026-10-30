import { Calculator, Database, FlaskConical, Ruler } from 'lucide-react'
import { Tooltip } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { Provenance, ProvenanceLevel } from '@/types/api'

export const PROVENANCE_META: Record<ProvenanceLevel, { short: string; icon: typeof Database; cls: string }> = {
  synthetic: { short: 'Synthetic demo data', icon: FlaskConical, cls: 'text-sun synthetic-edge bg-sun/5' },
  geometric_only: { short: 'Geometric only, no terrain', icon: Ruler, cls: 'text-muted border border-dashed border-rule' },
  analytic_approximate: { short: 'Approximate model', icon: Calculator, cls: 'text-signal border border-signal/40' },
  scientific_sourced: { short: 'Sourced scientific data', icon: Database, cls: 'text-both border border-both/40' },
}

export function ProvenanceBadge({ level, className }: { level: ProvenanceLevel; className?: string }) {
  const m = PROVENANCE_META[level]
  const Icon = m.icon
  return (
    <span className={cn('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium', m.cls, className)}>
      <Icon className="size-3.5" aria-hidden />
      {m.short}
    </span>
  )
}

/** Compact strip under a result: what the numbers are made of. */
export function ProvenanceStrip({ provenance }: { provenance: Provenance }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted">
      <ProvenanceBadge level={provenance.overall} />
      <Tooltip content={provenance.ephemeris.description}>
        <span className="cursor-help underline decoration-dotted underline-offset-2">
          Ephemeris: {provenance.ephemeris.name}
        </span>
      </Tooltip>
      <Tooltip content={provenance.terrain_mask_source}>
        <span className="cursor-help underline decoration-dotted underline-offset-2">
          Terrain: {provenance.terrain.name}
        </span>
      </Tooltip>
    </div>
  )
}
