import * as React from 'react'
import { cn } from '@/lib/utils'

/** Panel surface. Radius is intentionally small: these are instrument panels, not cards in a feed. */
export function Card({ className, interactive, ...props }: React.HTMLAttributes<HTMLElement> & { interactive?: boolean }) {
  return <section className={cn('rounded-lg border border-rule-soft bg-panel', interactive && 'lift', className)} {...props} />
}

export function CardHeader({
  title,
  description,
  actions,
  className,
}: {
  title: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <header className={cn('flex flex-wrap items-start justify-between gap-3 px-4 pt-3.5 pb-2', className)}>
      <div className="min-w-0">
        <h2 className="font-display text-[17px] font-semibold tracking-wide text-ink">{title}</h2>
        {description && <p className="mt-0.5 text-[13px] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  )
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-4 pb-4', className)} {...props} />
}
