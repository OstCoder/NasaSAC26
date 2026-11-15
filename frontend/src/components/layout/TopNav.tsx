import { BookOpen, Compass, Gauge, GitCompare, Map, Microscope, Type } from 'lucide-react'
import * as React from 'react'
import { useApp } from '@/hooks/useAppContext'
import { useDataSaver } from '@/hooks/useDataSaver'
import { cn } from '@/lib/utils'

export type View = 'planner' | 'science' | 'decision' | 'compare' | 'methodology'

const NAV: { id: View; label: string; short: string; icon: typeof Map; flag: string }[] = [
  { id: 'planner', label: 'Plan a landing', short: 'Plan', icon: Map, flag: 'mission_planner' },
  { id: 'science', label: 'Explore the Moon', short: 'Explore', icon: Microscope, flag: 'science_exploration' },
  { id: 'decision', label: 'Choose a site', short: 'Choose', icon: Compass, flag: 'decision_support' },
  { id: 'compare', label: 'Compare sites', short: 'Compare', icon: GitCompare, flag: 'scenario_comparison' },
  { id: 'methodology', label: 'How it works', short: 'Guide', icon: BookOpen, flag: 'methodology_page' },
]

function LunaMark() {
  return (
    <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
      <circle cx="16" cy="14" r="10" fill="none" stroke="#e4eaf4" strokeWidth="1.6" />
      <path d="M16 4a10 10 0 0 1 0 20a7 10 0 0 0 0-20z" fill="#f2b544" />
      <path d="M3 25h26" stroke="#4cc4e2" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export function TopNav({ view, onView, publicMode, setPublicMode }: { view: View; onView: (v: View) => void; publicMode: boolean; setPublicMode: (v: boolean) => void }) {
  const { features } = useApp()
  const [dataSaver, setDataSaver] = useDataSaver()
  const dataSaverRef = React.useRef(dataSaver)
  React.useEffect(() => { dataSaverRef.current = dataSaver }, [dataSaver])
  React.useEffect(() => {
    const on = () => setDataSaver(!dataSaverRef.current)
    window.addEventListener('lunanav:toggle-data-saver', on)
    return () => window.removeEventListener('lunanav:toggle-data-saver', on)
  }, [setDataSaver])
  const visible = NAV.filter((n) => features[n.flag] !== false)
  return (
    <>
      <header className="sticky top-0 z-[1100] border-b border-rule-soft bg-night/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <LunaMark />
            <div className="leading-tight">
              <p className="font-display text-xl font-bold tracking-wide">LunaNav</p>
              <p className="text-[11px] text-faint">Lunar landing site navigator</p>
            </div>
          </div>
          <nav aria-label="Main" className="hidden min-w-0 flex-1 flex-wrap gap-1 sm:flex">
            {visible.map((n) => (
              <button
                key={n.id}
                onClick={() => onView(n.id)}
                aria-current={view === n.id ? 'page' : undefined}
                className={cn(
                  'inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-md px-3 text-sm font-medium transition-colors',
                  view === n.id ? 'bg-raised text-ink' : 'text-muted hover:text-ink',
                )}
              >
                <n.icon className="size-4" aria-hidden />
                {n.label}
              </button>
            ))}
          </nav>
          <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:ml-auto sm:w-auto sm:justify-end">
            <button
              type="button"
              onClick={() => setDataSaver(!dataSaver)}
              aria-pressed={dataSaver}
              title={dataSaver ? 'Data saver on: smaller imagery, no 3D textures' : 'Data saver off'}
              className={cn(
                'inline-flex h-9 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors',
                dataSaver ? 'bg-sun/15 text-sun' : 'text-muted hover:text-ink',
              )}
            >
              <Gauge className="size-4" aria-hidden />
              <span className="hidden sm:inline">{dataSaver ? 'Data saver on' : 'Data saver'}</span>
            </button>
            <button
              type="button"
              onClick={() => setPublicMode(!publicMode)}
              aria-pressed={publicMode}
              title={publicMode ? 'Larger text is on' : 'Make the text larger'}
              className={cn(
                'inline-flex h-9 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors',
                publicMode ? 'bg-signal/15 text-signal' : 'text-muted hover:text-ink',
              )}
            >
              <Type className="size-4" aria-hidden />
              <span className="hidden sm:inline">{publicMode ? 'Larger text on' : 'Larger text'}</span>
            </button>
          </div>
        </div>
      </header>
      <nav aria-label="Main (mobile)" className="fixed inset-x-0 bottom-0 z-[1100] flex border-t border-rule-soft bg-night/95 backdrop-blur sm:hidden">
        <div className="mx-auto flex w-full max-w-[1500px] items-center justify-around px-2 py-1.5">
          {visible.map((n) => (
            <button
              key={n.id}
              onClick={() => onView(n.id)}
              aria-current={view === n.id ? 'page' : undefined}
              aria-label={n.label}
              className={cn(
                'flex flex-1 flex-col items-center gap-0.5 rounded-md px-1 py-1 text-[10px] font-medium transition-colors',
                view === n.id ? 'text-signal' : 'text-muted',
              )}
            >
              <n.icon className="size-5" aria-hidden />
              <span className="truncate">{n.short}</span>
            </button>
          ))}
        </div>
      </nav>
    </>
  )
}
