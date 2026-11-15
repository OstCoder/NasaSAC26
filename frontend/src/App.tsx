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

const VIEWS: View[] = ['planner', 'decision', 'compare', 'methodology']

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
  return (
    <div className="min-h-full">
      <TopNav view={view} onView={setView} />
      <main className="mx-auto max-w-[1500px] px-4 py-4">
        {view === 'planner' && <MissionPlannerPage onCompare={() => setView('compare')} />}
        {view === 'decision' && <DecisionDashboard />}
        {view === 'compare' && <ComparisonPage />}
        {view === 'methodology' && <MethodologyPage />}
      </main>
      <Footer />
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
