import { Check, Minus } from 'lucide-react'
import { ProvenanceBadge } from '@/components/ProvenanceBadge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { useApiResource } from '@/hooks/useApiResource'
import { useApp } from '@/hooks/useAppContext'
import { fmtUtc } from '@/lib/format'
import { api } from '@/services/api'
import type { EffectsIncluded, ProviderInfo } from '@/types/api'

const PIPELINE = [
  ['Ephemeris', 'Sub-solar and sub-Earth points on the Moon, with distances, from the active ephemeris provider.'],
  ['Local sky position', 'Converted to azimuth and elevation in the site’s East-North-Up frame, including parallax from the site’s offset from the Moon’s centre.'],
  ['Terrain skyline', 'The horizon mask gives the skyline elevation at every azimuth. A body is visible only when its centre clears that skyline.'],
  ['Intervals', 'Visible and blocked periods are found from the sign of the clearance, with edges interpolated between samples.'],
  ['Metrics', 'Totals, longest blackouts and times to set are computed from the intervals. Values touching the window edge are flagged as lower bounds.'],
]

const EFFECTS: { key: keyof EffectsIncluded; label: string }[] = [
  { key: 'terrain_topography', label: 'Real terrain topography' },
  { key: 'lunar_curvature_in_horizon', label: 'Lunar curvature in skyline' },
  { key: 'optical_libration', label: 'Optical libration' },
  { key: 'physical_libration', label: 'Physical libration' },
  { key: 'observer_parallax', label: 'Observer parallax' },
  { key: 'light_time_correction', label: 'Light-time correction' },
]

function Yes({ on }: { on: boolean }) {
  return on ? <Check className="mx-auto size-4 text-both" aria-label="included" /> : <Minus className="mx-auto size-4 text-faint" aria-label="not included" />
}

function ProviderRow({ p }: { p: ProviderInfo }) {
  return (
    <div className="border-t border-rule-soft py-3 first:border-t-0">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-medium text-ink">{p.name}</p>
        <ProvenanceBadge level={p.provenance} />
        <span className={p.available ? 'text-xs text-both' : 'text-xs text-alert'}>{p.available ? 'Available' : 'Not available'}</span>
      </div>
      <p className="mt-1 max-w-[75ch] text-sm text-muted">{p.description}</p>
      <p className="mt-1 text-xs text-faint">Source: {p.source}</p>
      {p.supported_start_utc && p.supported_end_utc && (
        <p className="num text-xs text-faint">Range: {fmtUtc(p.supported_start_utc)} to {fmtUtc(p.supported_end_utc)} UTC</p>
      )}
      {!p.available && p.unavailable_reason && <p className="mt-1 text-xs text-alert">{p.unavailable_reason}</p>}
    </div>
  )
}

export function MethodologyPage() {
  const { config } = useApp()
  const demo = useApiResource<ProviderInfo[]>('demo', () => api.providers('demo'), 0)
  const jpl = useApiResource<ProviderInfo[]>('jpl', () => api.providers('jpl'), 0)
  const sci = useApiResource<ProviderInfo[]>('scientific', () => api.providers('scientific'), 0)
  const all = [...(demo.data ?? []), ...(jpl.data ?? []), ...(sci.data ?? [])].filter(
    (p, i, arr) => arr.findIndex((q) => q.id === p.id) === i,
  )

  return (
    <div className="mx-auto max-w-[1100px] space-y-4">
      <Card>
        <CardHeader title="How LunaNav calculates visibility" />
        <CardContent>
          <ol className="grid gap-4 md:grid-cols-5">
            {PIPELINE.map(([t, d], i) => (
              <li key={t} className="border-l-2 border-rule pl-3">
                <p className="font-display text-sm font-semibold text-ink">
                  <span className="text-faint">{i + 1}.</span> {t}
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-muted">{d}</p>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader title="Demo mode" description="For exploring the interface and method. Skylines are invented." />
          <CardContent>{demo.data?.map((p) => <ProviderRow key={p.id} p={p} />)}</CardContent>
        </Card>
        <Card>
          <CardHeader title="JPL live mode" description="Live JPL Horizons geometry. Terrain applied only where LOLA masks exist; otherwise results are labelled geometric only." />
          <CardContent>{jpl.data?.map((p) => <ProviderRow key={p.id} p={p} />)}</CardContent>
        </Card>
        <Card>
          <CardHeader title="Scientific mode" description="Uses only sourced data. If a dataset is missing, results are withheld, never substituted." />
          <CardContent>{sci.data?.map((p) => <ProviderRow key={p.id} p={p} />)}</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader title="Effects included by each provider" />
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-rule text-[13px] text-muted">
                <th className="py-2 pr-3 text-left font-medium">Effect</th>
                {all.map((p) => (
                  <th key={p.id} className="px-2 py-2 text-center font-medium">{p.id.replace(/_/g, ' ')}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {EFFECTS.map((e) => (
                <tr key={e.key} className="border-b border-rule-soft last:border-0">
                  <td className="py-2 pr-3 text-ink">{e.label}</td>
                  {all.map((p) => (
                    <td key={p.id} className="px-2 py-2"><Yes on={Boolean(p.effects[e.key])} /></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-faint">
            Not modelled anywhere: refraction (no atmosphere), lander self-shadowing, panel and antenna pointing, link budgets.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader
          title="Mission requirements"
          description="Phase 1 thresholds from config/lunanav.config.json. The same values are served at GET /api/config and checked by POST /api/requirements; nothing is hardcoded in the UI."
        />
        <CardContent>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            {[
              ['Minimum sunlight availability', `\u2265 ${config.requirements.min_sun_visible_pct}% of the mission window`],
              ['Minimum Earth visibility', `\u2265 ${config.requirements.min_earth_visible_pct}% of the mission window`],
              ['Maximum Earth blackout', `\u2264 ${config.requirements.max_earth_blackout_hours} h without direct Earth line of sight`],
              [
                'PSR proximity',
                config.requirements.psr_proximity === 'preferred'
                  ? 'Optional scientific preference, not a pass/fail threshold'
                  : 'Optional factor',
              ],
            ].map(([k, v]) => (
              <div key={k} className="grid grid-cols-[170px_1fr] gap-3 border-t border-rule-soft pt-2 first:border-t-0 first:pt-0">
                <dt className="text-muted">{k}</dt>
                <dd className="text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 text-xs text-faint">{config.requirements.basis}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Conventions" />
          <CardContent>
            <dl className="space-y-2 text-sm">
              {[
                ['Frame', String(config.coordinates.frame)],
                ['Longitude', String(config.coordinates.longitude_convention)],
                ['Reference radius', `${config.coordinates.reference_radius_km} km`],
                ['Azimuth', 'Clockwise from local north. Near the south pole, north points toward the equator.'],
                ['Visibility rule', 'Body centre above the terrain skyline. The Sun’s partial disk is reported separately.'],
                ['Time', 'All times UTC. Supported window ' + fmtUtc(config.simulation.supported_start_utc) + ' to ' + fmtUtc(config.simulation.supported_end_utc) + '.'],
                ['Map', 'South polar stereographic on a 1737.4 km sphere; 0° (Earth-facing) at the top.'],
              ].map(([k, v]) => (
                <div key={k} className="grid grid-cols-[140px_1fr] gap-3 border-t border-rule-soft pt-2 first:border-t-0 first:pt-0">
                  <dt className="text-muted">{k}</dt>
                  <dd className="text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="What the results do not mean" />
          <CardContent className="space-y-2 text-sm leading-relaxed text-muted">
            <p>Sun above the skyline is a precondition for solar power, not a power estimate. Panel orientation, shadowing by the lander and dust are not modelled.</p>
            <p>Earth above the skyline is a precondition for direct-to-Earth links, not a link guarantee. Antenna pointing, ground-station coverage and relays are not modelled.</p>
            <p>Comparisons describe differences in modelled visibility. They are not site rankings or recommendations.</p>
            <p>Demo skylines are synthetic. Demo landing-site coordinates are approximate and are not official landing-region definitions.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader title="Scientific model labels" />
        <CardContent className="space-y-2 text-sm leading-relaxed text-muted">
          <p><strong className="text-ink">TERRAIN-AWARE MODEL</strong> — the result uses a committed LOLA terrain horizon. Sun/Earth clearance is the authoritative visibility calculation.</p>
          <p><strong className="text-ink">SIMPLIFIED ENERGY MODEL</strong> — the power and link budgets use configured array, battery and communications assumptions. They are not hardware performance predictions.</p>
          <p><strong className="text-ink">GEOMETRIC ONLY</strong> — no terrain mask covers this site or date. The result is the unobstructed geometric horizon and is not a terrain-adjusted visibility claim.</p>
          <p><strong className="text-ink">UNAVAILABLE / NOT ASSESSED</strong> — the committed data does not contain the value. It is left unknown, never imputed. A nearby PSR is not evidence of water ice, and no result here is a landing-safety or NASA-approval verdict.</p>
        </CardContent>
      </Card>
    </div>
  )
}
