import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useApp } from '@/hooks/useAppContext'
import { useReadiness, useSiteEngineering } from '@/hooks/useScenario'
import { api } from '@/services/api'
import { cn } from '@/lib/utils'
import type { LinkCase } from '@/types/api'

const WINDOWS = [
  { key: 'initial', label: '1–8 Dec 2026' },
  { key: 'alternative', label: '11–18 Dec 2026' },
] as const

type WindowKey = (typeof WINDOWS)[number]['key']

const num = (value: number | null | undefined, digits = 0) =>
  value == null ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits })

function linkRow(label: string, c: LinkCase | null) {
  if (!c) return null
  return (
    <tr key={label}>
      <td className="py-1 pr-3 text-muted">{label}</td>
      <td className="py-1 pr-3 num text-right text-ink">{num(c.range_km)} km</td>
      <td className="py-1 pr-3 num text-right text-ink">{num(c.cn0_db_hz, 1)} dB-Hz</td>
      <td className="py-1 pr-3 num text-right text-ink">{num(c.supported_rate_bps / 1e6, 2)} Mbps</td>
      <td className={cn('py-1 num text-right', c.margin_db >= 0 ? 'text-both' : 'text-sun')}>
        {num(c.margin_db, 1)} dB
      </td>
    </tr>
  )
}

/**
 * Phase 5: the solar-power and direct-to-Earth budgets for one candidate and
 * window, drawn from the committed track and the terrain-adjusted visibility.
 * Every number is an engineering estimate under the assumptions printed
 * beneath it — not a flight power budget and not a link budget for flown
 * hardware. Off while both experimental flags are off.
 */
export function EngineeringBudgetPanel() {
  const { features } = useApp()
  const enabled = Boolean(features.experimental_power_model || features.experimental_comm_link_budget)
  const readiness = useReadiness()
  const candidates = readiness.data?.sites ?? []
  const [picked, setPicked] = React.useState<string | null>(null)
  const siteId = picked ?? candidates[0]?.site_id ?? 'shackleton-rim'
  const [window, setWindow] = React.useState<WindowKey>('initial')
  const engineering = useSiteEngineering(siteId, window)

  const data = engineering.data
  const power = data?.power
  const link = data?.link
  const battery = power?.budget.battery
  const siteName = data?.site.name ?? siteId
  const aria = data
    ? `${siteName}, ${WINDOWS.find((w) => w.key === window)?.label ?? window}. ` +
      `Vertical array energy ${num(power?.budget.array_energy_wh)} watt-hours against a ` +
      `${num(power?.budget.load_wh)} watt-hour load; battery minimum ${num(battery?.min_soc_pct, 1)} percent. ` +
      (link?.closes
        ? `Link closes with ${num(link.worst_case?.margin_db, 1)} dB margin at ${num((link.worst_case?.supported_rate_bps ?? 0) / 1e6, 2)} Mbps worst case.`
        : 'Link does not close on the committed geometry.')
    : 'Engineering budget loading.'

  if (!enabled) return null

  return (
    <Card>
      <CardHeader
        title="Phase 5 · Power and link budget"
        description="Solar array energy and a direct-to-Earth X-band budget from the committed hourly track and the terrain-adjusted visibility. Engineering estimates under the assumptions printed below — not a flight power budget and not a negotiated communications link."
      />
      <CardContent className="space-y-4">
        {engineering.error && <ErrorNotice error={engineering.error} />}

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

        {!data ? (
          !engineering.error && <p className="text-sm text-muted">Loading engineering budget…</p>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <section aria-label="Power budget" className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Power</h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-faint">
                      <th className="py-1 pr-3 font-medium">Array</th>
                      <th className="py-1 pr-3 text-right font-medium">Peak</th>
                      <th className="py-1 pr-3 text-right font-medium">Energy</th>
                      <th className="py-1 text-right font-medium">Capacity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {power?.designs.map((design) => (
                      <tr key={design.id}>
                        <td className="py-1 pr-3 text-muted">
                          {design.label}
                          {design.id === power.design.recommended && (
                            <span className="ml-1 rounded-full border border-both/50 bg-both/10 px-1.5 text-[10px] text-both">
                              used
                            </span>
                          )}
                        </td>
                        <td className="py-1 pr-3 num text-right text-ink">{num(design.peak_w)} W</td>
                        <td className="py-1 pr-3 num text-right text-ink">{num(design.energy_wh)} Wh</td>
                        <td className="py-1 num text-right text-muted">{num(design.capacity_factor_pct, 1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {power && battery && (
                  <p className="text-xs text-muted" aria-live="polite">
                    Load {num(power.budget.load_w)} W over {num(power.window.hours)} h ={' '}
                    {num(power.budget.load_wh)} Wh; net {num(power.budget.net_wh)} Wh. Battery{' '}
                    {num(battery.capacity_wh)} Wh ({num(battery.usable_wh)} Wh usable), minimum{' '}
                    <span className={cn(battery.depleted ? 'text-sun' : 'text-both')}>
                      {num(battery.min_soc_pct, 1)}%
                    </span>
                    {battery.unserved_wh > 0 && `, ${num(battery.unserved_wh)} Wh unserved`}.
                  </p>
                )}
              </section>

              <section aria-label="Link budget" className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">
                  Direct to Earth · X-band
                </h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-faint">
                      <th className="py-1 pr-3 font-medium">Case</th>
                      <th className="py-1 pr-3 text-right font-medium">Range</th>
                      <th className="py-1 pr-3 text-right font-medium">C/N0</th>
                      <th className="py-1 pr-3 text-right font-medium">Rate</th>
                      <th className="py-1 text-right font-medium">Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {linkRow('Best', link?.best_case ?? null)}
                    {linkRow('Worst', link?.worst_case ?? null)}
                  </tbody>
                </table>
                {link && (
                  <p className="text-xs text-muted" aria-live="polite">
                    Earth line of sight {num(link.window.visible_hours, 1)} h; data volume bound{' '}
                    {num(link.window.data_volume_bound_mb, 1)} MB; {num(link.window.outage_hours, 1)} h outage.
                    Mode: {link.assumptions.modulation}.
                  </p>
                )}
              </section>
            </div>

            {battery && (
              <p className={cn('text-xs', battery.depleted ? 'text-sun' : 'text-muted')}>{battery.verdict}</p>
            )}
            {link && <p className={cn('text-xs', link.closes ? 'text-muted' : 'text-sun')}>{link.verdict}</p>}

            <details className="rounded border border-rule-soft bg-panel-raised/40 px-3 py-2 text-xs">
              <summary className="cursor-pointer text-muted">Assumptions behind these numbers</summary>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-faint">
                <li>Power: {power?.assumptions.basis}</li>
                <li>Link: {link?.assumptions.basis}</li>
              </ul>
            </details>

            <p className="text-xs">
              <a
                className="text-earth underline underline-offset-2"
                href={api.missionReportUrl({ siteId, window })}
                download={`lunanav-${siteId}-${window}.md`}
              >
                Download the mission report (.md)
              </a>{' '}
              <span className="text-faint">
                — terrain basis, visibility, requirement checks, both budgets and the limits, in one file.
              </span>
            </p>
            <p className="sr-only" aria-live="polite">
              {aria}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
