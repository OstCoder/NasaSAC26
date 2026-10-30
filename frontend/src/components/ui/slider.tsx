import * as SliderPrimitive from '@radix-ui/react-slider'
import * as React from 'react'
import { cn } from '@/lib/utils'

export function Slider({ className, ...props }: React.ComponentProps<typeof SliderPrimitive.Root>) {
  return (
    <SliderPrimitive.Root
      className={cn('relative flex h-5 w-full touch-none select-none items-center', className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1 w-full grow overflow-hidden rounded-full bg-rule">
        <SliderPrimitive.Range className="absolute h-full bg-signal/70" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        aria-label="Inspect time"
        className="block size-4 rounded-full border-2 border-signal bg-night shadow transition-transform hover:scale-110"
      />
    </SliderPrimitive.Root>
  )
}
