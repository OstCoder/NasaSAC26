import { cn } from '@/lib/utils'

/** Shimmer placeholder. Uses the .skeleton animation from index.css. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton rounded-md', className)} aria-hidden />
}