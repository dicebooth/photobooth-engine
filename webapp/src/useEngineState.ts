import { useEffect, useState } from 'react'
import { api, EngineState, UnauthorizedError } from './api'

export type Connection = 'connecting' | 'online' | 'offline' | 'unauthorized'

const RETRY_MS = 2000

/**
 * Keeps the engine state in sync through Server-Sent Events.
 * EventSource does not expose HTTP status codes, so the token is validated with a plain request
 * before opening the stream and again whenever the stream is closed for good (e.g. engine restarted
 * with a new token).
 */
export function useEngineState(token: string | null) {
  const [state, setState] = useState<EngineState | null>(null)
  const [connection, setConnection] = useState<Connection>('connecting')

  useEffect(() => {
    if (!token) return
    let source: EventSource | null = null
    let retryTimer: number | undefined
    let cancelled = false

    const scheduleRetry = () => {
      retryTimer = window.setTimeout(connect, RETRY_MS)
    }

    const connect = async () => {
      try {
        const initial = await api.state(token)
        if (cancelled) return
        setState(initial)
      } catch (err) {
        if (cancelled) return
        if (err instanceof UnauthorizedError) {
          setConnection('unauthorized')
          return
        }
        setConnection('offline')
        scheduleRetry()
        return
      }

      source = new EventSource(api.eventsUrl(token))
      source.onopen = () => setConnection('online')
      source.onmessage = (e) => {
        setState(JSON.parse(e.data))
        setConnection('online')
      }
      source.onerror = () => {
        setConnection('offline')
        // CONNECTING means the browser is retrying on its own, CLOSED means it gave up
        if (source?.readyState === EventSource.CLOSED) {
          source.close()
          scheduleRetry()
        }
      }
    }

    setConnection('connecting')
    connect()

    return () => {
      cancelled = true
      window.clearTimeout(retryTimer)
      source?.close()
    }
  }, [token])

  return { state, connection }
}
