import * as TabsPrimitive from '@radix-ui/react-tabs'
import * as React from 'react'
import { cn } from '@/lib/utils'

export const Tabs = TabsPrimitive.Root

export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn('inline-flex items-center gap-0.5 rounded-md border border-rule-soft bg-night p-0.5', className)}
      {...props}
    />
  )
}

export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        'inline-flex h-7 items-center gap-1.5 rounded px-2.5 text-[13px] font-medium text-muted transition-colors hover:text-ink data-[state=active]:bg-raised data-[state=active]:text-ink [&_svg]:size-3.5',
        className,
      )}
      {...props}
    />
  )
}

export const TabsContent = TabsPrimitive.Content
