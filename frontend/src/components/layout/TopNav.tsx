import { BookOpen, GitCompare, Map } from 'lucide-react'
import { JplStatusPill } from '@/components/JplStatus'
import { useApp } from '@/hooks/useAppContext'
import { cn } from '@/lib/utils'
import type { Mode } from '@/types/api'

export type View = 'planner' | 'compare' | 'methodology'

const NAV: { id: View; label: string; icon: typeof Map; flag: string }[] = [
  { id: 'planner', label: 'Mission planner', icon: Map, flag: 'mission_planner' },
  { id: 'compare', label: 'Compare scenarios', icon: GitCompare, flag: 'scenario_comparison' },
  { id: 'methodology', label: 'Data & methodology', icon: BookOpen, flag: 'methodology_page' },
]

const MODE_LABEL: Record<Mode, string> = { demo: 'Demo data', jpl: 'JPL live', scientific: 'Scientific' }
const MODE_HINT: Record<Mode, string> = {
  demo: 'Approximate built-in ephemeris with synthetic terrain. Works offline.',
  jpl: 'Live Sun and Earth positions from JPL Horizons. Terrain only where LOLA masks exist.',
  scientific: 'JPL Horizons plus LOLA terrain masks. Refuses to compute if either is missing.',
}

function LunaMark() {
  // Crescent with a horizon line: the product is about what sits above a horizon.
  return (
    <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
      <circle cx="16" cy="14" r="10" fill="none" stroke="#e4eaf4" strokeWidth="1.6" />
      <path d="M16 4a10 10 0 0 1 0 20a7 10 0 0 0 0-20z" fill="#f2b544" />
      <path d="M3 25h26" stroke="#4cc4e2" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export function TopNav({ view, onView }: { view: View; onView: (v: View) => void }) {
  const { features, mode, setMode, config } = useApp()
  return (
    <header className="sticky top-0 z-[1100] border-b border-rule-soft bg-night/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <LunaMark />
          <div className="leading-tight">
            <p className="font-display text-xl font-bold tracking-wide">LunaNav</p>
            <p className="text-[11px] text-faint">Lunar landing site navigator</p>
          </div>
        </div>
        <nav aria-label="Main" className="flex flex-1 flex-wrap gap-1">
          {NAV.filter((n) => features[n.flag] !== false).map((n) => (
            <button
              key={n.id}
              onClick={() => onView(n.id)}
              aria-current={view === n.id ? 'page' : undefined}
              className={cn(
                'inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors',
                view === n.id ? 'bg-raised text-ink' : 'text-muted hover:text-ink',
              )}
            >
              <n.icon className="size-4" aria-hidden />
              {n.label}
            </button>
          ))}
        </nav>
        <JplStatusPill />
        <div role="radiogroup" aria-label="Data mode" className="flex items-center gap-1 rounded-md border border-rule-soft p-0.5">
          {config.mode.allowed.map((m: Mode) => (
            <button
              key={m}
              role="radio"
              aria-checked={mode === m}
              onClick={() => setMode(m)}
              className={cn(
                'h-7 rounded px-2.5 text-[13px] font-medium capitalize transition-colors',
                mode === m
                  ? { demo: 'bg-sun/15 text-sun', jpl: 'bg-signal/20 text-signal', scientific: 'bg-both/15 text-both' }[m]
                  : 'text-muted hover:text-ink',
              )}
              title={MODE_HINT[m]}
            >
              {MODE_LABEL[m]}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
