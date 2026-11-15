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
import { nextTransition, zoomDomain } from './timeline'

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

interface TimelineProps {
  result: ScenarioResult
  index: number
  onIndex: (i: number) => void
}

/**
 * Elevation/clearance chart + Sun/Earth/Both interval bands + time scrubber.
 * `index` is the inspected sample in result.series; all children share it.
 */
export function VisibilityTimeline(props: TimelineProps) {
  if (props.result.series.times_utc.length === 0) {
    return (
      <div role="status" className="rounded-md border border-rule-soft p-4 text-sm text-muted">
        No timeline samples were returned for this scenario. The chart, intervals and cursor are
        hidden rather than filled with assumed values.
      </div>
    )
  }
  return <TimelineView {...props} />
}

function TimelineView({ result, index, onIndex }: TimelineProps) {
  const [view, setView] = React.useState<View>('clearance')
  const [playing, setPlaying] = React.useState(false)
  const [speed, setSpeed] = React.useState(1)
  const [zoomHours, setZoomHours] = React.useState<number | null>(null)
  const indexRef = React.useRef(index)
  const onIndexRef = React.useRef(onIndex)
  indexRef.current = index
  onIndexRef.current = onIndex
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

  // Playback reads the current sample from a ref. Without that, the parent's
  // inline onIndex callback restarted this timer on every sample and playback
  // slowed to a crawl. Speed is a sample multiplier, not a fabricated sample.
  React.useEffect(() => {
    if (!playing) return
    const step = Math.max(1, Math.round((n / 240) * speed))
    const id = window.setInterval(() => {
      const next = Math.min(n - 1, indexRef.current + step)
      onIndexRef.current(next)
      if (next >= n - 1) setPlaying(false)
    }, 80)
    return () => window.clearInterval(id)
  }, [playing, n, speed])

  const cursorT = Date.parse(s.times_utc[index])
  const pickFrac = (f: number) => onIndex(Math.max(0, Math.min(n - 1, Math.round(f * (n - 1)))))

  // Zoom is a view-only window centred on the inspected sample. The interval bands
  // below stay at full-mission scale, so zooming never hides a blackout.
  const domain = React.useMemo<[number, number]>(
    () => zoomDomain(t0, t1, cursorT, zoomHours),
    [zoomHours, cursorT, t0, t1],
  )

  const next = React.useMemo(() => nextTransition(result.intervals, cursorT), [result.intervals, cursorT])

  const ticks = React.useMemo(() => {
    const spanDays = (domain[1] - domain[0]) / 86_400_000
    const unit = spanDays > 4 ? 86_400_000 : spanDays > 1 ? 21_600_000 : 3_600_000
    const first = Math.ceil(domain[0] / unit) * unit
    const out: number[] = []
    for (let t = first; t <= domain[1]; t += unit) out.push(t)
    const stride = Math.max(1, Math.ceil(out.length / 10))
    return out.filter((_, i) => i % stride === 0)
  }, [domain])
  const tickFmt = (v: number) => {
    const d = new Date(v)
    const spanDays = (domain[1] - domain[0]) / 86_400_000
    if (spanDays > 4)
      return `${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`
    if (spanDays > 1)
      return `${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}h`
    return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
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

      {t1 - t0 > 6 * 3_600_000 && (
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Timeline zoom">
          <span className="text-[13px] text-muted">Time range</span>
          {([
            [null, 'Full mission'],
            [72, '3 d'],
            [24, '24 h'],
            [6, '6 h'],
          ] as const).map(([hours, label]) => (
            <Button
              key={label}
              size="sm"
              variant={zoomHours === hours ? 'secondary' : 'ghost'}
              aria-pressed={zoomHours === hours}
              onClick={() => setZoomHours(hours)}
            >
              {label}
            </Button>
          ))}
          {zoomHours !== null && <span className="text-xs text-faint">centred on the selected time</span>}
        </div>
      )}

      <div
        className="h-[200px] w-full"
        role="img"
        aria-label={`Sun and Earth ${view === 'clearance' ? 'clearance above terrain' : 'geometric elevation'} from ${fmtUtc(s.times_utc[0])} to ${fmtUtc(s.times_utc[n - 1])} UTC. Inspected time ${fmtUtc(s.times_utc[index])} UTC. Use the time controls below the chart to inspect other samples.`}
      >
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 6, right: 12, bottom: 0, left: -8 }}
            onClick={(state: unknown) => {
              const label = (state as { activeLabel?: number | string } | null)?.activeLabel
              if (label === undefined) return
              const frac = (Number(label) - domain[0]) / (domain[1] - domain[0])
              pickFrac(Math.max(0, Math.min(1, frac)))
            }}
          >
            <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="2 4" />
            <XAxis dataKey="t" type="number" domain={domain} allowDataOverflow scale="time"
              tickFormatter={tickFmt} ticks={ticks} stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} />
            <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} width={44} tickFormatter={(v: number) => `${v}°`} />
            <ReferenceLine y={0} stroke={CHART_COLORS.terrainEdge} strokeWidth={1.2} />
            <ReferenceLine x={cursorT} stroke={CHART_COLORS.cursor} strokeWidth={1.5} />
            {next && next.time >= domain[0] && next.time <= domain[1] && (
              <ReferenceLine x={next.time} stroke={CHART_COLORS.sun} strokeDasharray="4 3" strokeWidth={1} />
            )}
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

      <div className="flex flex-wrap items-center gap-2 pl-[36px]">
        <Button size="icon" variant="ghost" aria-label="Previous sample" onClick={() => onIndex(Math.max(0, index - 1))}>
          <StepBack />
        </Button>
        <Button size="icon" variant="secondary" aria-label={playing ? 'Pause' : 'Play through mission'}
          onClick={() => {
            if (index >= n - 1) {
              indexRef.current = 0
              onIndexRef.current(0)
            }
            setPlaying((p) => !p)
          }}>
          {playing ? <Pause /> : <Play />}
        </Button>
        <Button size="icon" variant="ghost" aria-label="Next sample" onClick={() => onIndex(Math.min(n - 1, index + 1))}>
          <StepForward />
        </Button>
        <Slider className="mx-2 flex-1" min={0} max={n - 1} step={1} value={[index]} onValueChange={([v]) => onIndex(v)} />
        <div role="group" aria-label="Playback speed" className="flex items-center gap-1">
          <span className="text-[11px] text-faint">Speed</span>
          {[0.5, 1, 2, 4].map((value) => (
            <Button
              key={value}
              size="sm"
              variant={speed === value ? 'secondary' : 'ghost'}
              aria-pressed={speed === value}
              onClick={() => setSpeed(value)}
            >
              {value}×
            </Button>
          ))}
        </div>
        <span className="num w-[150px] shrink-0 text-right text-sm text-ink">{fmtUtc(s.times_utc[index])} UTC</span>
      </div>

      <p className="pl-[36px] text-xs text-faint" aria-live="polite">
        {next ? `Next modelled edge: ${next.label} at ${fmtUtc(new Date(next.time).toISOString())} UTC.` : 'No visibility edge remains in this window.'}
        {' '}The dashed amber rule marks it when it is inside the current chart range.
      </p>
    </div>
  )
}
