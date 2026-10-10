import { useEffect, useState } from 'react'
import { api, EngineState } from '../api'
import { CopiesPicker } from './CopiesPicker'

interface Props {
  state: EngineState
  token: string
  disabled: boolean
}

export function vibrate() {
  navigator.vibrate?.(25)
}

export function ActionPanel({ state, token, disabled }: Props) {
  const { phase } = state
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // every new request from the engine starts from a clean slate
  useEffect(() => {
    setPending(false)
    setError(null)
  }, [phase])

  const send = async (action: () => Promise<unknown>) => {
    vibrate()
    setPending(true)
    setError(null)
    try {
      await action()
    } catch (err) {
      setPending(false)
      setError(err instanceof Error ? err.message : 'Errore inatteso')
    }
  }

  const locked = disabled || pending

  return (
    <footer className="panel">
      {error && <p className="panel-error">{error}</p>}

      {phase === 'approval' && (
        <div className="panel-row">
          <button className="btn btn-reject" disabled={locked} onClick={() => send(() => api.approve(token, false))}>
            ✕ Scarta
          </button>
          <button className="btn btn-approve" disabled={locked} onClick={() => send(() => api.approve(token, true))}>
            ✓ Approva
          </button>
        </div>
      )}

      {phase === 'copies' && (
        <CopiesPicker
          limits={state.copies}
          disabled={locked}
          resetKey={state.preview.id}
          onConfirm={(copies) => send(() => api.copies(token, copies))}
          secondaryAction={
            <button
              className="btn btn-secondary btn-back"
              disabled={locked}
              onClick={() => send(() => api.back(token))}
              aria-label="Annulla la conferma e torna all'anteprima"
            >
              ↩ Indietro
            </button>
          }
        />
      )}

      {(phase === 'waiting_shot' || phase === 'processing' || phase === 'idle') && (
        <div className="panel-info">
          <span className="spinner" aria-hidden="true" />
          {phase === 'waiting_shot' ? 'Pronto per il prossimo scatto' : 'Elaborazione in corso'}
        </div>
      )}
    </footer>
  )
}
