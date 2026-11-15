import * as React from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CHART_COLORS } from '@/config/app'
import { fmtUtc } from '@/lib/format'
import type { EngineeringBudget } from '@/types/api'
import { blockedSpans, chargingSpans, dischargingSpans, toEnergyPoints, type EnergyPoint } from './energySeries'

const num = (value: number | null | undefined, digits = 0) =>
  value == null ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits })

function EnergyTip({ active, payload }: {
  active?: boolean
  payload?: { payload: EnergyPoint }[]
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-md border border-rule bg-raised px-2.5 py-1.5 text-xs">
      <p className="num mb-1 text-muted">{fmtUtc(new Date(p.t).toISOString())} UTC</p>
      <p className="num text-sun">Array {num(p.solar)} W</p>
      <p className="num text-muted">Load {num(p.load)} W</p>
      <p className="num text-both">Battery {num(p.soc, 1)}%</p>
      {p.unserved > 0 && <p className="num text-alert">Unserved {num(p.unserved)} Wh</p>}
      <p className="text-faint">Sun {p.sun ? 'above skyline' : 'below skyline'}</p>
    </div>
  )
}

function tickFormat(value: number) {
  const d = new Date(value)
  return `${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ` +
    `${String(d.getUTCHours()).padStart(2, '0')}h`
}

/**
 * Per-sample solar generation and battery state. Shaded spans are Sun below
 * the terrain skyline; they are not a second, inferred irradiance model.
 */
export function EnergyTimeline({ power }: { power: EngineeringBudget['power'] }) {
  const series = power.series
  const points = React.useMemo(() => toEnergyPoints(series), [series])
  const spans = React.useMemo(() => blockedSpans(series), [series])
  const chargeSpans = React.useMemo(() => chargingSpans(series), [series])
  const dischargeSpans = React.useMemo(() => dischargingSpans(series), [series])
  const battery = power.budget.battery
  const extremes = power.extremes

  if (!points.length) {
    return (
      <div role="status" className="rounded-md border border-rule-soft p-4 text-sm text-muted">
        No aligned power samples were returned. The energy timeline is hidden rather than filled with
        assumed values.
      </div>
    )
  }

  const start = points[0].t
  const end = points[points.length - 1].t
  const timeTick = (value: number) => tickFormat(value)
  const reserve = battery.reserve_pct
  const minSoc = battery.min_soc_pct

  return (
    <section aria-label="Battery energy timeline" className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Energy timeline</h3>
        <p className="text-xs text-faint">
          {power.design.selected === 'fixed'
            ? `Fixed array · tilt ${num(power.design.tilt_deg, 0)}°, facing ${num(power.design.azimuth_deg, 0)}°`
            : power.design.tracking ? 'Vertical array · azimuth-tracking' : 'Horizontal array'}
          {' '}· {num(power.budget.load_w)} W load · grey = Sun below skyline · green/orange = charging/discharging
        </p>
      </div>

      <div
        className="h-[190px] w-full"
        role="img"
        aria-label={`Solar array power and load from ${fmtUtc(series.times_utc[0])} to ${fmtUtc(series.times_utc[points.length - 1])} UTC. Shaded spans mark Sun below the terrain skyline.`}
      >
        <ResponsiveContainer>
          <ComposedChart data={points} margin={{ top: 6, right: 12, bottom: 0, left: -8 }}>
            <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="2 4" />
            <XAxis
              dataKey="t"
              type="number"
              domain={[start, end]}
              scale="time"
              tickFormatter={timeTick}
              stroke={CHART_COLORS.axis}
              tick={{ fontSize: 11 }}
              minTickGap={28}
            />
            <YAxis
              stroke={CHART_COLORS.axis}
              tick={{ fontSize: 11 }}
              width={44}
              tickFormatter={(value: number) => `${value} W`}
            />
            {spans.map((span) => (
              <ReferenceArea
                key={`${span.x1}-${span.x2}`}
                x1={span.x1}
                x2={span.x2}
                fill={CHART_COLORS.terrain}
                fillOpacity={0.28}
                stroke="none"
              />
            ))}
            <ReferenceLine y={power.budget.load_w} stroke={CHART_COLORS.earth} strokeDasharray="4 3" />
            <RTooltip content={<EnergyTip />} cursor={{ stroke: CHART_COLORS.axis, strokeDasharray: '3 3' }} />
            <Area
              dataKey="solar"
              stroke={CHART_COLORS.sun}
              fill={CHART_COLORS.sun}
              fillOpacity={0.12}
              strokeWidth={1.4}
              isAnimationActive={false}
              name="Array power"
            />
            <Line
              dataKey="load"
              stroke={CHART_COLORS.earth}
              dot={false}
              strokeWidth={1.2}
              isAnimationActive={false}
              name="Load"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div
        className="h-[150px] w-full"
        role="img"
        aria-label={`Battery state of charge, minimum ${num(minSoc, 1)} percent against a ${num(reserve, 1)} percent reserve.`}
      >
        <ResponsiveContainer>
          <ComposedChart data={points} margin={{ top: 6, right: 12, bottom: 0, left: -8 }}>
            <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="2 4" />
            <XAxis
              dataKey="t"
              type="number"
              domain={[start, end]}
              scale="time"
              tickFormatter={timeTick}
              stroke={CHART_COLORS.axis}
              tick={{ fontSize: 11 }}
              minTickGap={28}
            />
            <YAxis
              stroke={CHART_COLORS.axis}
              tick={{ fontSize: 11 }}
              width={44}
              domain={[0, 100]}
              tickFormatter={(value: number) => `${value}%`}
            />
            {spans.map((span) => (
              <ReferenceArea
                key={`${span.x1}-${span.x2}`}
                x1={span.x1}
                x2={span.x2}
                fill={CHART_COLORS.terrain}
                fillOpacity={0.28}
                stroke="none"
              />
            ))}
            {chargeSpans.map((span) => (
              <ReferenceArea
                key={`charge-${span.x1}-${span.x2}`}
                x1={span.x1}
                x2={span.x2}
                fill={CHART_COLORS.both}
                fillOpacity={0.08}
                stroke="none"
              />
            ))}
            {dischargeSpans.map((span) => (
              <ReferenceArea
                key={`discharge-${span.x1}-${span.x2}`}
                x1={span.x1}
                x2={span.x2}
                fill={CHART_COLORS.sun}
                fillOpacity={0.05}
                stroke="none"
              />
            ))}
            <ReferenceLine y={reserve} stroke={CHART_COLORS.earth} strokeDasharray="4 3" />
            <ReferenceLine y={minSoc} stroke={CHART_COLORS.sun} strokeDasharray="2 3" />
            <RTooltip content={<EnergyTip />} cursor={{ stroke: CHART_COLORS.axis, strokeDasharray: '3 3' }} />
            <Area
              dataKey="soc"
              stroke={CHART_COLORS.both}
              fill={CHART_COLORS.both}
              fillOpacity={0.12}
              strokeWidth={1.6}
              isAnimationActive={false}
              name="Battery state of charge"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-muted">
        Minimum battery <span className={battery.depleted ? 'text-sun' : 'text-both'}>{num(minSoc, 1)}%</span>
        {' '}at {fmtUtc(series.times_utc[extremes.min_battery_index] ?? series.times_utc[0])} UTC;
        reserve {num(reserve, 1)}%. {extremes.shortage_samples > 0
          ? `${extremes.shortage_samples} samples (${num(extremes.shortage_hours, 1)} h) have array output below load.`
          : 'Array output is at or above load in every sample.'}
      </p>
    </section>
  )
}
