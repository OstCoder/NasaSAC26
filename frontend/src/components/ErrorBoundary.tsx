import * as React from 'react'

/**
 * Keeps a failing panel from taking the whole app down. Used around optional,
 * heavy features (3D viewer) whose failure must stay local.
 */
export class ErrorBoundary extends React.Component<
  { fallback: (error: Error, reset: () => void) => React.ReactNode; children: React.ReactNode; resetKey?: unknown },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidUpdate(prev: { resetKey?: unknown }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null })
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('LunaNav panel error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) return this.props.fallback(this.state.error, () => this.setState({ error: null }))
    return this.props.children
  }
}
