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
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CHART_COLORS } from '@/config/app'
import { useReadiness, useSiteHorizon, useSiteSeries } from '@/hooks/useScenario'
import { cn } from '@/lib/utils'
import type { TerrainBodyComparison } from '@/types/api'

const WINDOWS = [
  { key: 'initial', label: '1–8 Dec 2026' },
  { key: 'alternative', label: '11–18 Dec 2026' },
] as const

type WindowKey = (typeof WINDOWS)[number]['key']

const COMPASS: Record<number, string> = {
  0: 'N', 45: 'NE', 90: 'E', 135: 'SE', 180: 'S', 225: 'SW', 270: 'W', 315: 'NW', 360: 'N',
}

interface TrackPoint {
  az: number
  el: number
}

const dot = (fill: string, opacity: number) =>
  function TrackDot({ cx, cy }: { cx?: number; cy?: number }) {
    return cx === undefined || cy === undefined ? null : (
      <circle cx={cx} cy={cy} r={1.6} fill={fill} fillOpacity={opacity} />
    )
  }

function compareLine(label: string, c: TerrainBodyComparison | null): string | null {
  if (!c) return null
  if (c.above_skyline === 0) {
    return `${label}: the skyline is above all ${c.samples} samples (highest ${c.elevation_max_deg.toFixed(2)}° vs ${c.skyline_min_deg.toFixed(2)}° at the lowest skyline), so this window has none.`
  }
  const blocked = c.blocked_by_terrain
  return `${label}: ${c.above_skyline} of ${c.samples} samples above the skyline (${Math.round(c.above_skyline_pct)}%)${
    blocked > 0 ? `; terrain blocks ${blocked} that a flat 0° horizon would have counted` : ''
  }.`
}

/**
 * Phase 4 Task 1: the terrain horizon profile for one candidate and window,
 * with the Sun and Earth tracks drawn straight onto it. The `terrain` /
 * `geometric only` label comes from the payload, never inferred from the site
 * name, and the coverage numbers sit next to the chart because a profile
 * without its pixel size and range is not a measurement.
 */
export function TerrainHorizonPanel() {
  const readiness = useReadiness()
  const candidates = readiness.data?.sites ?? []
  const [picked, setPicked] = React.useState<string | null>(null)
  const siteId = picked ?? candidates[0]?.site_id ?? 'shackleton-rim'
  const [window, setWindow] = React.useState<WindowKey>('initial')
  const horizon = useSiteHorizon(siteId, window)
  const track = useSiteSeries(siteId, window)

  const report = horizon.data
  const terrain = report?.terrain
  const error = horizon.error ?? track.error

  const chart = React.useMemo(() => {
    const profile = terrain
      ? [
          ...terrain.profile.azimuth_deg.map((az, i) => ({ az, terrain: terrain.profile.elevation_deg[i] })),
          { az: 360, terrain: terrain.profile.elevation_deg[0] },
        ]
      : []
    const sun: TrackPoint[] = []
    const earth: TrackPoint[] = []
    for (const record of track.data?.series ?? []) {
      sun.push({ az: record.sun.azimuth_deg, el: record.sun.elevation_deg })
      earth.push({ az: record.earth.azimuth_deg, el: record.earth.elevation_deg })
    }
    const highs = [
      ...(terrain?.profile.elevation_deg ?? []),
      ...sun.map((p) => p.el),
      ...earth.map((p) => p.el),
    ]
    const low = terrain?.profile.elevation_deg.length ? Math.min(...terrain.profile.elevation_deg) : 0
    const yDomain: [number, number] = [Math.min(-2, Math.floor(low - 0.5)), Math.max(3, Math.ceil(Math.max(...highs, 0) + 0.75))]
    return { profile, sun, earth, yDomain }
  }, [terrain, track.data])

  const geometricOnly = terrain?.geometric_only ?? false
  const siteName = report?.site.name ?? siteId
  const maxObs = terrain?.summary.max_obstruction_deg
  const maxAz = terrain?.summary.max_obstruction_azimuth_deg
  const aria = React.useMemo(() => {
    if (!terrain) return 'Terrain horizon profile loading.'
    const parts = [
      `${siteName}, ${WINDOWS.find((w) => w.key === window)?.label ?? window}.`,
      terrain.available
        ? `Terrain horizon from ${terrain.coverage.near.pixel_m ?? '?'} m near and ${terrain.coverage.far.pixel_m ?? '?'} m far LOLA data to ${terrain.coverage.max_sampled_range_km ?? '?'} km, observer ${terrain.observer_height_m} m.`
        : 'No terrain profile: flat geometric horizon only.',
      maxObs !== undefined ? `Maximum obstruction ${maxObs.toFixed(2)} degrees.` : '',
      compareLine('Sun', report?.comparison.sun ?? null) ?? '',
      compareLine('Earth', report?.comparison.earth ?? null) ?? '',
    ]
    return parts.filter(Boolean).join(' ')
  }, [terrain, siteName, window, maxObs, report])

  return (
    <Card>
      <CardHeader
        title="Phase 4 · Terrain horizon profile"
        description="The committed LOLA skyline for one candidate, with the Sun and Earth tracks drawn on top at their own azimuths. Points above the grey terrain are clear of it; points below are blocked. Geometry only — Sun above terrain is not power, Earth above terrain is not a link budget."
      />
      <CardContent className="space-y-4">
        {error && <ErrorNotice error={error} />}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Candidate site">
            {candidates.map((site) => (
              <Button
                key={site.site_id}
                size="sm"
                variant={site.site_id === siteId ? 'secondary' : 'ghost'}
                aria-pressed={site.site_id === siteId}
                onClick={() => setPicked(site.site_id)}
              >
                {site.name ?? site.site_id}
              </Button>
            ))}
          </div>
          <Tabs value={window} onValueChange={(v) => setWindow(v as WindowKey)}>
            <TabsList aria-label="Mission window">
              {WINDOWS.map((w) => (
                <TabsTrigger key={w.key} value={w.key}>
                  {w.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        {!report ? (
          !error && <p className="text-sm text-muted">Loading terrain horizon…</p>
        ) : (
          <>
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
              <span
                className={cn(
                  'rounded-full border px-2 py-0.5 font-medium',
                  geometricOnly
                    ? 'border-sun/50 bg-sun/10 text-sun'
                    : 'border-both/50 bg-both/10 text-both',
                )}
                title={
                  geometricOnly
                    ? 'No committed LOLA skyline covers this point: the profile is flat by construction.'
                    : 'Committed two-tier LOLA skyline applied.'
                }
              >
                {geometricOnly ? 'geometric only' : 'terrain'}
              </span>
              <span className="num text-ink">
                {siteName} · {terrain?.surface_elevation_m == null ? '—' : `${terrain.surface_elevation_m.toFixed(0)} m`}
              </span>
              <span className="num text-muted">observer {terrain?.observer_height_m} m</span>
              <span className="num text-muted">
                {terrain?.coverage.near.pixel_m ?? '—'} m near / {terrain?.coverage.far.pixel_m ?? '—'} m far
                {terrain?.coverage.max_sampled_range_km != null ? ` to ${terrain.coverage.max_sampled_range_km} km` : ''}
              </span>
              {maxObs !== undefined && (
                <span className="num text-muted">
                  max {maxObs.toFixed(2)}°{maxAz != null ? ` at ${Math.round(maxAz)}° ${COMPASS[Math.round(maxAz / 45) * 45] ?? ''}` : ''}
                </span>
              )}
            </div>

            <div style={{ height: 280 }} className="w-full" role="img" aria-label={aria}>
              <ResponsiveContainer>
                <ComposedChart data={chart.profile} margin={{ top: 12, right: 12, bottom: 4, left: -8 }}>
                  <defs>
                    <linearGradient id="horizonTerrainFill" x1="0" y1="0" x2="0" y2="1">
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
                    domain={chart.yDomain}
                    allowDataOverflow
                    stroke={CHART_COLORS.axis}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${v}°`}
                    width={44}
                  />
                  <Area
                    dataKey="terrain"
                    type="linear"
                    baseValue={chart.yDomain[0]}
                    fill="url(#horizonTerrainFill)"
                    stroke={CHART_COLORS.terrainEdge}
                    strokeWidth={1.2}
                    isAnimationActive={false}
                  />
                  <ReferenceLine
                    y={0}
                    stroke={CHART_COLORS.axis}
                    strokeDasharray="5 4"
                    label={{ value: 'geometric horizon', position: 'insideTopRight', fill: CHART_COLORS.axis, fontSize: 10 }}
                  />
                  <Scatter data={chart.sun} dataKey="el" isAnimationActive={false} shape={dot(CHART_COLORS.sun, 0.85)} />
                  <Scatter data={chart.earth} dataKey="el" isAnimationActive={false} shape={dot(CHART_COLORS.earth, 0.85)} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-1 text-xs">
              <p className="flex items-center gap-2 text-muted">
                <span className="inline-block size-2 rounded-full" style={{ background: CHART_COLORS.sun }} aria-hidden />
                {compareLine('Sun', report.comparison.sun) ?? 'Sun track unavailable.'}
              </p>
              <p className="flex items-center gap-2 text-muted">
                <span className="inline-block size-2 rounded-full" style={{ background: CHART_COLORS.earth }} aria-hidden />
                {compareLine('Earth', report.comparison.earth) ?? 'Earth track unavailable.'}
              </p>
              {geometricOnly ? (
                <p className="text-sun">
                  {report.visibility.reason ?? 'No LOLA skyline covers this point, so this profile is a flat 0° assumption, not a measurement.'}
                </p>
              ) : (
                <p className="text-faint">
                  A skyline above the Sun's highest elevation in a window means no sunlight under the terrain rule
                  for that whole window. Azimuth is clockwise from local north. Vertical scale is
                  exaggerated; the numbers above are the measurement.
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
