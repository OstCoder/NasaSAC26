import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-150 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 press',
  {
    variants: {
      variant: {
        primary: 'bg-signal text-night hover:bg-signal/90',
        secondary: 'bg-raised text-ink border border-rule hover:bg-rule-soft',
        ghost: 'text-muted hover:text-ink hover:bg-raised',
        outline: 'border border-rule text-ink hover:bg-raised',
      },
      size: { sm: 'h-8 px-2.5', md: 'h-9 px-3.5', icon: 'size-8' },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
