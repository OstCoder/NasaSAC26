import { Earth, Sun } from 'lucide-react'
import { Tooltip } from '@/components/ui/tooltip'
import { fmtDeg, fmtHours, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { BodyState, Snapshot } from '@/types/api'
import { bodyStatus } from './bodyStatus'

function Row({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  const content = (
    <div
      className="flex items-baseline justify-between gap-3 border-t border-rule-soft py-1.5 first:border-t-0 focus-visible:outline-2 focus-visible:outline-signal"
      tabIndex={hint ? 0 : undefined}
    >
      <dt className="text-[13px] text-muted">{label}</dt>
      <dd className="num text-sm text-ink">{value}</dd>
    </div>
  )
  return hint ? <Tooltip content={hint}>{content}</Tooltip> : content
}

function BodyReadout({ body, state, lookahead }: { body: 'sun' | 'earth'; state: BodyState; lookahead: number }) {
  const status = bodyStatus(state)
  const isSun = body === 'sun'
  const Icon = isSun ? Sun : Earth
  const eventName = isSun
    ? state.transition_kind === 'rise' ? 'sunrise' : 'sunset'
    : state.transition_kind === 'rise' ? 'Earthrise' : 'Earthset'
  return (
    <div className="min-w-0 flex-1">
      <div className="mb-2 flex items-center gap-2">
        <Icon className={cn('size-5', isSun ? 'text-sun' : 'text-earth')} aria-hidden />
        <h3 className="font-display text-base font-semibold">{isSun ? 'Sun' : 'Earth'}</h3>
        <span
          className={cn(
            'rounded-md px-2.5 py-1 text-sm font-semibold',
            status.tone === 'visible'
              ? isSun
                ? 'bg-sun/20 text-sun'
                : 'bg-earth/20 text-earth'
              : status.tone === 'terrain'
                ? 'hatch-blocked bg-raised text-ink'
                : 'bg-raised text-faint',
          )}
        >
          {status.label}
        </span>
      </div>
      <dl>
        <Row label="Elevation (geometric)" value={fmtDeg(state.elevation_deg)} hint="Elevation relative to the flat local horizon. Positive is geometric visibility only when terrain is absent." />
        <Row label="Azimuth" value={fmtDeg(state.azimuth_deg, 1)} hint="Clockwise from local north, which points toward the lunar equator at the south pole." />
        <Row label="Terrain skyline at that azimuth" value={fmtDeg(state.terrain_horizon_deg)} hint="LOLA-derived obstruction height in this direction. Zero means a flat horizon was used." />
        <Row
          label="Clearance above terrain"
          value={
            <span className={cn(state.clearance_deg > 0 ? 'text-ink' : 'text-alert', 'text-base font-bold')}>
              {fmtDeg(state.clearance_deg)}
            </span>
          }
          hint="Body elevation minus the skyline at its azimuth. Visible means clearance is above zero; it is not a power or link-budget estimate."
        />
        {isSun && state.disk_fraction !== null && (
          <Row label="Solar disk above skyline" value={`${Math.round(state.disk_fraction * 100)}%`} hint="Share of the Sun’s disk above the skyline. The visibility verdict still uses the disk centre." />
        )}
        <Row
          label={`Next ${eventName}`}
          value={
            state.next_transition_utc ? (
              <span>
                {state.hours_until_transition !== null ? `in ${fmtHours(state.hours_until_transition)}` : 'scheduled'}
                <span className="block text-xs text-muted">{fmtUtc(state.next_transition_utc)} UTC</span>
              </span>
            ) : (
              <span className="text-muted">beyond {fmtHours(lookahead)}</span>
            )
          }
          hint={`The next modelled change in ${isSun ? 'Sun' : 'Earth'} visibility within the ${fmtHours(lookahead)} look-ahead. “Beyond” means none was found, not that none will occur.`}
        />
      </dl>
    </div>
  )
}

export function SnapshotPanel({ snapshot }: { snapshot: Snapshot }) {
  return (
    <div className="flex flex-col gap-5 sm:flex-row sm:gap-6">
      <BodyReadout body="sun" state={snapshot.sun} lookahead={snapshot.lookahead_hours} />
      <div className="hidden w-px bg-rule-soft sm:block" />
      <BodyReadout body="earth" state={snapshot.earth} lookahead={snapshot.lookahead_hours} />
    </div>
  )
}
