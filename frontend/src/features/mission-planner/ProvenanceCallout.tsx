import { ChevronDown } from 'lucide-react'
import * as React from 'react'
import { PROVENANCE_META } from '@/components/ProvenanceBadge'
import { cn } from '@/lib/utils'
import type { Provenance } from '@/types/api'

/** One-line statement of what the numbers are, expandable to the full caveat list. */
export function ProvenanceCallout({ provenance }: { provenance: Provenance }) {
  const [open, setOpen] = React.useState(false)
  const meta = PROVENANCE_META[provenance.overall]
  const Icon = meta.icon
  return (
    <div className={cn('rounded-lg bg-panel px-4 py-2.5', meta.cls)}>
      <button className="flex w-full items-center gap-2.5 text-left text-sm" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <Icon className="size-4 shrink-0" aria-hidden />
        <span className="font-medium">{provenance.label}</span>
        <span className="ml-auto hidden text-xs text-muted sm:inline">{open ? 'Hide' : 'What this includes'}</span>
        <ChevronDown className={cn('size-4 text-muted transition-transform', open && 'rotate-180')} aria-hidden />
      </button>
      {open && (
        <ul className="mt-2 space-y-1 border-t border-rule-soft pt-2 text-[13px] leading-relaxed text-muted">
          {provenance.caveats.map((c) => (
            <li key={c} className="flex gap-2">
              <span className="mt-2 size-1 shrink-0 rounded-full bg-faint" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
