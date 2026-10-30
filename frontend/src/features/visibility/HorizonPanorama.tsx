import * as React from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  XAxis,
  YAxis,
} from 'recharts'
import { CHART_COLORS } from '@/config/app'
import type { ScenarioResult } from '@/types/api'

const COMPASS: Record<number, string> = { 0: 'N', 45: 'NE', 90: 'E', 135: 'SE', 180: 'S', 225: 'SW', 270: 'W', 315: 'NW', 360: 'N' }

interface Pt {
  az: number
  el: number
}

function thin<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = arr.length / max
  return Array.from({ length: max }, (_, i) => arr[Math.floor(i * step)])
}

const dot = (fill: string, opacity: number) =>
  function TrackDot({ cx, cy }: { cx?: number; cy?: number }) {
    return cx === undefined || cy === undefined ? null : <circle cx={cx} cy={cy} r={1.7} fill={fill} fillOpacity={opacity} />
  }

function Marker({ cx, cy, fill, ring }: { cx?: number; cy?: number; fill: string; ring: string }) {
  if (cx === undefined || cy === undefined) return null
  return (
    <g>
      <circle cx={cx} cy={cy} r={11} fill="none" stroke={ring} strokeWidth={1.5} strokeDasharray="2 2" />
      <circle cx={cx} cy={cy} r={6.5} fill={fill} stroke="#0d1524" strokeWidth={1.5} />
    </g>
  )
}

/**
 * 360° horizon panorama: terrain skyline (filled), the geometric horizon (0°),
 * and the Sun/Earth tracks over the mission window. Solid track dots are above
 * the terrain; faint dots are blocked. Elevation is vertically exaggerated.
 */
export function HorizonPanorama({ result, index, height = 260 }: { result: ScenarioResult; index: number; height?: number }) {
  const { series, horizon_mask: mask } = result

  const terrain = React.useMemo(() => {
    const pts = mask.azimuth_deg.map((az, i) => ({ az, terrain: mask.elevation_deg[i] }))
    return [...pts, { az: 360, terrain: mask.elevation_deg[0] }]
  }, [mask])

  const tracks = React.useMemo(() => {
    const out = { sunVis: [] as Pt[], sunHid: [] as Pt[], earthVis: [] as Pt[], earthHid: [] as Pt[] }
    series.times_utc.forEach((_, i) => {
      const s = { az: series.sun_azimuth_deg[i], el: series.sun_elevation_deg[i] }
      const e = { az: series.earth_azimuth_deg[i], el: series.earth_elevation_deg[i] }
      ;(series.sun_visible[i] ? out.sunVis : out.sunHid).push(s)
      ;(series.earth_visible[i] ? out.earthVis : out.earthHid).push(e)
    })
    return {
      sunVis: thin(out.sunVis, 500),
      sunHid: thin(out.sunHid, 500),
      earthVis: thin(out.earthVis, 500),
      earthHid: thin(out.earthHid, 500),
    }
  }, [series])

  const yDomain = React.useMemo(() => {
    const hi = Math.max(...series.earth_elevation_deg, ...series.sun_elevation_deg, ...mask.elevation_deg)
    const lo = Math.min(...mask.elevation_deg)
    return [Math.min(-2, Math.floor(lo - 0.5)), Math.max(3, Math.ceil(hi + 0.75))]
  }, [series, mask])

  const sunNow = [{ az: series.sun_azimuth_deg[index], el: series.sun_elevation_deg[index] }]
  const earthNow = [{ az: series.earth_azimuth_deg[index], el: series.earth_elevation_deg[index] }]

  return (
    <div style={{ height }} className="w-full" role="img"
      aria-label={`Horizon panorama. Sun at azimuth ${sunNow[0].az.toFixed(0)}°, elevation ${sunNow[0].el.toFixed(1)}°. Earth at azimuth ${earthNow[0].az.toFixed(0)}°, elevation ${earthNow[0].el.toFixed(1)}°.`}>
      <ResponsiveContainer>
        <ComposedChart data={terrain} margin={{ top: 12, right: 12, bottom: 4, left: -8 }}>
          <defs>
            <linearGradient id="terrainFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4a5a76" stopOpacity={0.95} />
              <stop offset="100%" stopColor="#1b2639" stopOpacity={1} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="2 4" />
          <XAxis
            type="number"
            dataKey="az"
            domain={[0, 360]}
            ticks={[0, 45, 90, 135, 180, 225, 270, 315, 360]}
            tickFormatter={(v: number) => `${COMPASS[v] ?? ''} ${v}°`}
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 11 }}
            allowDataOverflow
          />
          <YAxis
            type="number"
            domain={yDomain}
            allowDataOverflow
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v}°`}
            width={44}
          />
          <Area
            dataKey="terrain"
            type="linear"
            baseValue={yDomain[0]}
            fill="url(#terrainFill)"
            stroke={CHART_COLORS.terrainEdge}
            strokeWidth={1.2}
            isAnimationActive={false}
          />
          <ReferenceLine y={0} stroke={CHART_COLORS.axis} strokeDasharray="5 4"
            label={{ value: 'geometric horizon', position: 'insideTopRight', fill: CHART_COLORS.axis, fontSize: 10 }} />
          <Scatter data={tracks.sunHid} dataKey="el" isAnimationActive={false} shape={dot(CHART_COLORS.sun, 0.2)} />
          <Scatter data={tracks.earthHid} dataKey="el" isAnimationActive={false} shape={dot(CHART_COLORS.earth, 0.2)} />
          <Scatter data={tracks.sunVis} dataKey="el" isAnimationActive={false} shape={dot(CHART_COLORS.sun, 0.9)} />
          <Scatter data={tracks.earthVis} dataKey="el" isAnimationActive={false} shape={dot(CHART_COLORS.earth, 0.9)} />
          <Scatter data={earthNow} dataKey="el" isAnimationActive={false}
            shape={(p: { cx?: number; cy?: number }) => <Marker {...p} fill={CHART_COLORS.earth} ring={CHART_COLORS.earth} />} />
          <Scatter data={sunNow} dataKey="el" isAnimationActive={false}
            shape={(p: { cx?: number; cy?: number }) => <Marker {...p} fill={CHART_COLORS.sun} ring={CHART_COLORS.sun} />} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
