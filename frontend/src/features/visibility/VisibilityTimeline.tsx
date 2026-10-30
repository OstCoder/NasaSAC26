import { Pause, Play, StepBack, StepForward } from 'lucide-react'
import * as React from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CHART_COLORS } from '@/config/app'
import { fmtDeg, fmtUtc } from '@/lib/format'
import type { ScenarioResult } from '@/types/api'
import { IntervalBands } from './IntervalBands'

type View = 'clearance' | 'geometric'

const MAX_POINTS = 700

function ChartTip({ active, payload, view }: {
  active?: boolean
  payload?: { payload: { t: number; sun: number; earth: number } }[]
  view: View
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-md border border-rule bg-raised px-2.5 py-1.5 text-xs">
      <p className="num mb-1 text-muted">{fmtUtc(new Date(p.t).toISOString())} UTC</p>
      <p className="num text-sun">Sun {fmtDeg(p.sun)} {view === 'clearance' ? 'above terrain' : 'elevation'}</p>
      <p className="num text-earth">Earth {fmtDeg(p.earth)} {view === 'clearance' ? 'above terrain' : 'elevation'}</p>
    </div>
  )
}

/**
 * Elevation/clearance chart + Sun/Earth/Both interval bands + time scrubber.
 * `index` is the inspected sample in result.series; all children share it.
 */
export function VisibilityTimeline({
  result,
  index,
  onIndex,
}: {
  result: ScenarioResult
  index: number
  onIndex: (i: number) => void
}) {
  const [view, setView] = React.useState<View>('clearance')
  const [playing, setPlaying] = React.useState(false)
  const s = result.series
  const n = s.times_utc.length
  const t0 = Date.parse(s.times_utc[0])
  const t1 = Date.parse(s.times_utc[n - 1])

  const data = React.useMemo(() => {
    const stride = Math.max(1, Math.ceil(n / MAX_POINTS))
    const rows = []
    for (let i = 0; i < n; i += stride) {
      rows.push({
        t: Date.parse(s.times_utc[i]),
        i,
        sun: view === 'clearance' ? s.sun_elevation_deg[i] - s.sun_terrain_horizon_deg[i] : s.sun_elevation_deg[i],
        earth: view === 'clearance' ? s.earth_elevation_deg[i] - s.earth_terrain_horizon_deg[i] : s.earth_elevation_deg[i],
      })
    }
    return rows
  }, [s, n, view])

  // playback
  React.useEffect(() => {
    if (!playing) return
    const step = Math.max(1, Math.round(n / 240))
    const id = window.setInterval(() => {
      onIndex(Math.min(n - 1, index + step))
    }, 80)
    if (index >= n - 1) setPlaying(false)
    return () => window.clearInterval(id)
  }, [playing, index, n, onIndex])

  const cursorT = Date.parse(s.times_utc[index])
  const pickFrac = (f: number) => onIndex(Math.max(0, Math.min(n - 1, Math.round(f * (n - 1)))))
  const days = (t1 - t0) / 86_400_000
  // Ticks on whole UTC days (or 6-hour marks for short missions), at most ~10.
  const ticks = React.useMemo(() => {
    const unit = days > 4 ? 86_400_000 : 21_600_000
    const count = (t1 - t0) / unit
    const stride = Math.max(1, Math.ceil(count / 10))
    const first = Math.ceil(t0 / unit) * unit
    const out: number[] = []
    for (let t = first; t <= t1; t += unit * stride) out.push(t)
    return out
  }, [t0, t1, days])
  const tickFmt = (v: number) => {
    const d = new Date(v)
    return days > 4
      ? `${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`
      : `${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}h`
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Tabs value={view} onValueChange={(v) => setView(v as View)}>
          <TabsList aria-label="Chart quantity">
            <TabsTrigger value="clearance">Height above terrain</TabsTrigger>
            <TabsTrigger value="geometric">Geometric elevation</TabsTrigger>
          </TabsList>
        </Tabs>
        <p className="text-xs text-faint">
          {view === 'clearance'
            ? 'Above 0° means the body clears the skyline at its azimuth.'
            : 'Relative to a flat horizon. Positive does not mean visible.'}
        </p>
      </div>

      <div className="h-[200px] w-full">
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 6, right: 12, bottom: 0, left: -8 }}
            onClick={(state: unknown) => {
              const label = (state as { activeLabel?: number | string } | null)?.activeLabel
              if (label !== undefined) pickFrac((Number(label) - t0) / (t1 - t0))
            }}
          >
            <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="2 4" />
            <XAxis dataKey="t" type="number" domain={[t0, t1]} scale="time" tickFormatter={tickFmt} ticks={ticks}
              stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} />
            <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} width={44} tickFormatter={(v: number) => `${v}°`} />
            <ReferenceLine y={0} stroke={CHART_COLORS.terrainEdge} strokeWidth={1.2} />
            <ReferenceLine x={cursorT} stroke={CHART_COLORS.cursor} strokeWidth={1.5} />
            <RTooltip content={<ChartTip view={view} />} cursor={{ stroke: CHART_COLORS.axis, strokeDasharray: '3 3' }} />
            <Line dataKey="sun" stroke={CHART_COLORS.sun} dot={false} strokeWidth={1.6} isAnimationActive={false} name="Sun" />
            <Line dataKey="earth" stroke={CHART_COLORS.earth} dot={false} strokeWidth={1.6} isAnimationActive={false} name="Earth" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="pl-[36px]">
        <IntervalBands
          intervals={result.intervals}
          windowStart={result.landing_utc}
          windowEnd={result.end_utc}
          cursorFrac={(cursorT - t0) / (t1 - t0)}
          onPick={pickFrac}
        />
      </div>

      <div className="flex items-center gap-2 pl-[36px]">
        <Button size="icon" variant="ghost" aria-label="Previous sample" onClick={() => onIndex(Math.max(0, index - 1))}>
          <StepBack />
        </Button>
        <Button size="icon" variant="secondary" aria-label={playing ? 'Pause' : 'Play through mission'}
          onClick={() => { if (index >= n - 1) onIndex(0); setPlaying((p) => !p) }}>
          {playing ? <Pause /> : <Play />}
        </Button>
        <Button size="icon" variant="ghost" aria-label="Next sample" onClick={() => onIndex(Math.min(n - 1, index + 1))}>
          <StepForward />
        </Button>
        <Slider className="mx-2 flex-1" min={0} max={n - 1} step={1} value={[index]} onValueChange={([v]) => onIndex(v)} />
        <span className="num w-[150px] shrink-0 text-right text-sm text-ink">{fmtUtc(s.times_utc[index])} UTC</span>
      </div>
    </div>
  )
}
