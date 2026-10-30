import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium [&_svg]:size-3.5', {
  variants: {
    tone: {
      neutral: 'bg-raised text-muted',
      sun: 'bg-sun/15 text-sun',
      earth: 'bg-earth/15 text-earth',
      both: 'bg-both/15 text-both',
      alert: 'bg-alert/15 text-alert',
      signal: 'bg-signal/15 text-signal',
      blocked: 'bg-raised text-faint',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
