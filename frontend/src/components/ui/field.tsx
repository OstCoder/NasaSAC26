import * as React from 'react'
import { cn } from '@/lib/utils'

export function Field({ label, hint, children, className }: {
  label: string
  hint?: React.ReactNode
  children: React.ReactNode
  className?: string
}) {
  const id = React.useId()
  const child = React.isValidElement<{ id?: string }>(children)
    ? React.cloneElement(children, { id: children.props.id ?? id })
    : children
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <label htmlFor={id} className="text-[13px] text-muted">{label}</label>
      {child}
      {hint && <p className="text-xs text-faint">{hint}</p>}
    </div>
  )
}

const control =
  'h-9 w-full rounded-md border border-rule bg-night px-2.5 text-sm text-ink placeholder:text-faint focus:border-signal focus:outline-none'

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(control, 'num', className)} {...props} />
}

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(control, 'pr-7', className)} {...props} />
}
