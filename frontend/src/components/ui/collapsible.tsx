import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Progressive disclosure wrapper. Uses native <details> so it is keyboard and
 * screen-reader accessible without extra state. Motion is gated by the global
 * prefers-reduced-motion guard.
 */
export function Collapsible({
  summary,
  children,
  className,
  defaultOpen = false,
}: {
  summary: React.ReactNode
  children: React.ReactNode
  className?: string
  defaultOpen?: boolean
}) {
  return (
    <details className={cn('group', className)} open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-ink [&::-webkit-details-marker]:hidden">
        <ChevronDown className="size-4 transition-transform duration-200 group-open:rotate-180" aria-hidden />
        {summary}
      </summary>
      <div className="mt-2 text-sm leading-relaxed text-muted">{children}</div>
    </details>
  )
}