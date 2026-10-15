import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  getHello,
  getStatus,
  logout,
  setOnUnauthorized,
  type SessionStatus,
} from './api/client'

type View =
  | { kind: 'loading' }
  | { kind: 'signed-out' }
  | { kind: 'signed-in'; user: NonNullable<SessionStatus['user']>; message: string | null; error: string | null }
  | { kind: 'error'; message: string }

export default function App() {
  const [view, setView] = useState<View>({ kind: 'loading' })

  const refresh = useCallback(async () => {
    try {
      const status = await getStatus()
      if (!status.authenticated || !status.user) {
        setView({ kind: 'signed-out' })
        return
      }
      try {
        const hello = await getHello()
        setView({ kind: 'signed-in', user: status.user, message: hello.message, error: null })
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : 'Could not load greeting'
        setView({ kind: 'signed-in', user: status.user, message: null, error: msg })
      }
    } catch (e) {
      setView({ kind: 'error', message: e instanceof Error ? e.message : 'Unknown error' })
    }
  }, [])

  useEffect(() => {
    setOnUnauthorized(() => setView({ kind: 'signed-out' }))
    void refresh()
  }, [refresh])

  const onLogin = () => {
    window.location.href = `/api/v1/auth/login?return_to=${encodeURIComponent(window.location.pathname)}`
  }
  const onLogout = async () => {
    await logout()
    setView({ kind: 'signed-out' })
  }

  return (
    <main className="card" aria-live="polite">
      {view.kind === 'loading' && <p>Loading…</p>}

      {view.kind === 'signed-out' && (
        <>
          <h1>Hello World</h1>
          <p>Please sign in to see your greeting.</p>
          <button type="button" onClick={onLogin}>Sign in</button>
        </>
      )}

      {view.kind === 'signed-in' && (
        <>
          <h1>{view.message ?? 'Hello, world!'}</h1>
          {view.error && <p className="error" role="alert">{view.error}</p>}
          <p className="muted">Signed in as {view.user.name} ({view.user.email})</p>
          <button type="button" onClick={onLogout}>Sign out</button>
        </>
      )}

      {view.kind === 'error' && (
        <>
          <h1>Something went wrong</h1>
          <p className="error" role="alert">{view.message}</p>
          <button type="button" onClick={() => { void refresh() }}>Try again</button>
        </>
      )}
    </main>
  )
}
