import { Earth, Sun } from 'lucide-react'
import { fmtDeg, fmtHours, fmtUtc } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { BodyState, Snapshot } from '@/types/api'
import { bodyStatus } from './bodyStatus'

function Row({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-rule-soft py-1.5 first:border-t-0" title={hint}>
      <dt className="text-[13px] text-muted">{label}</dt>
      <dd className="num text-sm text-ink">{value}</dd>
    </div>
  )
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
            'ml-auto rounded px-1.5 py-0.5 text-xs font-medium',
            status.tone === 'visible' && (isSun ? 'bg-sun/15 text-sun' : 'bg-earth/15 text-earth'),
            status.tone === 'terrain' && 'hatch-blocked bg-raised text-ink',
            status.tone === 'below' && 'bg-raised text-faint',
          )}
        >
          {status.label}
        </span>
      </div>
      <dl>
        <Row label="Elevation (geometric)" value={fmtDeg(state.elevation_deg)} hint="Relative to the flat local horizon" />
        <Row label="Azimuth" value={fmtDeg(state.azimuth_deg, 1)} hint="Clockwise from local north (toward the equator)" />
        <Row label="Terrain skyline at that azimuth" value={fmtDeg(state.terrain_horizon_deg)} />
        <Row
          label="Clearance above terrain"
          value={<span className={state.clearance_deg > 0 ? 'text-ink' : 'text-alert'}>{fmtDeg(state.clearance_deg)}</span>}
        />
        {isSun && state.disk_fraction !== null && (
          <Row label="Solar disk above skyline" value={`${Math.round(state.disk_fraction * 100)}%`} />
        )}
        <Row
          label={`Time until ${eventName}`}
          value={
            state.hours_until_transition !== null ? (
              <span title={state.next_transition_utc ? `${fmtUtc(state.next_transition_utc)} UTC` : undefined}>
                {fmtHours(state.hours_until_transition)}
              </span>
            ) : (
              <span className="text-muted">beyond {fmtHours(lookahead)}</span>
            )
          }
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
