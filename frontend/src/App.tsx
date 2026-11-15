import { LoaderCircle, RotateCw } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { TopNav, type View } from '@/components/layout/TopNav'
import { Button } from '@/components/ui/button'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ComparisonPage } from '@/features/comparison'
import { DecisionDashboard } from '@/features/decision'
import { MethodologyPage } from '@/features/methodology/MethodologyPage'
import { MissionPlannerPage } from '@/features/mission-planner/MissionPlannerPage'
import { AppProvider } from '@/hooks/useAppContext'

const VIEWS: View[] = ['planner', 'science', 'decision', 'compare', 'methodology']

const SciencePage = React.lazy(() => import('@/features/science/SciencePage'))

const DATA_SOURCES = [
  { label: 'NASA LROC QuickMap', href: 'https://quickmap.lroc.asu.edu/' },
  { label: 'NASA Moon Trek', href: 'https://trek.nasa.gov/moon/' },
  { label: 'NASA JPL Horizons', href: 'https://ssd.jpl.nasa.gov/horizons/' },
  { label: 'NASA LOLA south-pole topography', href: 'https://pgda.gsfc.nasa.gov/products/78' },
  { label: 'Canadian Space Agency lunar exploration', href: 'https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/' },
]

function Footer() {
  return (
    <footer className="mt-8 border-t border-rule-soft bg-night/80">
      <div className="mx-auto max-w-[1500px] space-y-2 px-4 py-5 text-xs text-faint">
        <p className="max-w-[100ch] leading-relaxed">
          Visibility is modelled geometry: the Sun or Earth centre above the LOLA skyline. It is not
          generated power, a communication link budget, or a landing-safety assessment. Demo skylines
          are synthetic; entries that are not sourced are labelled as such.
        </p>
        <nav aria-label="NASA data sources" className="flex flex-wrap gap-x-4 gap-y-1">
          <a className="text-muted underline-offset-2 hover:text-ink hover:underline" href="#methodology">
            Data &amp; methodology
          </a>
          {DATA_SOURCES.map((source) => (
            <a
              key={source.href}
              className="text-muted underline-offset-2 hover:text-ink hover:underline"
              href={source.href}
              target="_blank"
              rel="noreferrer"
            >
              {source.label}
            </a>
          ))}
        </nav>
        <p>LunaNav · NASA Space Apps Challenge 2026. Not affiliated with or endorsed by NASA.</p>
      </div>
    </footer>
  )
}

function useHashView(): [View, (v: View) => void] {
  const read = () => {
    const h = window.location.hash.replace('#', '') as View
    return VIEWS.includes(h) ? h : 'planner'
  }
  const [view, setView] = React.useState<View>(read)
  React.useEffect(() => {
    const on = () => setView(read())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return [view, (v) => { window.location.hash = v; setView(v) }]
}

function Shell() {
  const [view, setView] = useHashView()
  const [helpOpen, setHelpOpen] = React.useState(false)
  const mainRef = React.useRef<HTMLElement>(null)
  React.useEffect(() => {
    mainRef.current?.focus()
  }, [view])
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === '?') { setHelpOpen((o) => !o); return }
      if (e.key === 'Escape') { setHelpOpen(false); return }
      const views: View[] = ['planner', 'science', 'decision', 'compare', 'methodology']
      const n = Number(e.key)
      if (n >= 1 && n <= 5) { setView(views[n - 1]); return }
      if (e.key.toLowerCase() === 'c') window.dispatchEvent(new Event('lunanav:copy-link'))
      if (e.key.toLowerCase() === 'd') window.dispatchEvent(new Event('lunanav:toggle-data-saver'))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setView])
  return (
    <div className="min-h-full">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[1200] focus:rounded-md focus:bg-raised focus:px-3 focus:py-2 focus:text-sm focus:text-ink"
      >
        Skip to main content
      </a>
      <TopNav view={view} onView={setView} />
      <main ref={mainRef} id="main" tabIndex={-1} className="mx-auto max-w-[1500px] px-4 py-4 outline-none">
        <div key={view} className="fade-in">
          {view === 'planner' && <MissionPlannerPage onCompare={() => setView('compare')} />}
          {view === 'science' && (
            <React.Suspense fallback={<p className="text-sm text-muted">Loading science context…</p>}>
              <SciencePage />
            </React.Suspense>
          )}
          {view === 'decision' && <DecisionDashboard />}
          {view === 'compare' && <ComparisonPage />}
          {view === 'methodology' && <MethodologyPage />}
        </div>
      </main>
      <Footer />
      {helpOpen && (
        <div
          className="fixed inset-0 z-[1300] grid place-items-center bg-night/70 backdrop-blur-sm"
          onClick={() => setHelpOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard shortcuts"
        >
          <div className="w-full max-w-md rounded-lg border border-rule-soft bg-panel p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-ink">Keyboard shortcuts</h2>
              <button type="button" onClick={() => setHelpOpen(false)} className="text-muted hover:text-ink" aria-label="Close">✕</button>
            </div>
            <ul className="space-y-1.5 text-sm text-muted">
              <li><kbd className="rounded bg-raised px-1.5 py-0.5 text-xs text-ink">1</kbd>–<kbd className="rounded bg-raised px-1.5 py-0.5 text-xs text-ink">5</kbd> switch views (Planner, Science, Decision, Compare, Methodology)</li>
              <li><kbd className="rounded bg-raised px-1.5 py-0.5 text-xs text-ink">?</kbd> toggle this help</li>
              <li><kbd className="rounded bg-raised px-1.5 py-0.5 text-xs text-ink">Esc</kbd> close dialogs</li>
              <li><kbd className="rounded bg-raised px-1.5 py-0.5 text-xs text-ink">C</kbd> copy scenario link (on the planner)</li>
              <li><kbd className="rounded bg-raised px-1.5 py-0.5 text-xs text-ink">D</kbd> toggle data-saver mode</li>
            </ul>
            <p className="mt-3 text-xs text-faint">Tip: site selection also works from the keyboard-accessible "Landing site" dropdown in the scenario editor.</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default function App() {
  return (
    <TooltipProvider>
      <AppProvider
        fallback={(boot, retry) => (
          <div className="grid min-h-full place-items-center p-6">
            {boot.state === 'loading' ? (
              <p className="flex items-center gap-2 text-muted"><LoaderCircle className="size-4 animate-spin" /> Loading LunaNav…</p>
            ) : (
              <div className="w-full max-w-lg space-y-3">
                <ErrorNotice error={boot.error} />
                <Button onClick={retry}><RotateCw /> Try again</Button>
              </div>
            )}
          </div>
        )}
      >
        <Shell />
      </AppProvider>
    </TooltipProvider>
  )
}
