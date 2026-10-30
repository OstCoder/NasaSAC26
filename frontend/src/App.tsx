import { LoaderCircle, RotateCw } from 'lucide-react'
import * as React from 'react'
import { ErrorNotice } from '@/components/ErrorNotice'
import { TopNav, type View } from '@/components/layout/TopNav'
import { Button } from '@/components/ui/button'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ComparisonPage } from '@/features/comparison'
import { MethodologyPage } from '@/features/methodology/MethodologyPage'
import { MissionPlannerPage } from '@/features/mission-planner/MissionPlannerPage'
import { AppProvider } from '@/hooks/useAppContext'

const VIEWS: View[] = ['planner', 'compare', 'methodology']

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
        {view === 'compare' && <ComparisonPage />}
        {view === 'methodology' && <MethodologyPage />}
      </main>
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
