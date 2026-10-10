import { EngineState } from '../api'
import { Connection } from '../useEngineState'

interface Props {
  state: EngineState | null
  connection: Connection
  onOpenGallery: () => void
}

function Indicator({ label, ok }: { label: string; ok: boolean | null }) {
  const cls = ok === null ? 'unknown' : ok ? 'ok' : 'ko'
  return (
    <span className={`indicator ${cls}`} title={`${label}: ${ok === null ? 'verifica...' : ok ? 'ok' : 'non disponibile'}`}>
      <span className="dot" />
      {label}
    </span>
  )
}

export function Header({ state, connection, onOpenGallery }: Props) {
  return (
    <header className="header">
      <div className="header-title">
        <span className={`live-dot ${connection}`} aria-label={connection === 'online' ? 'connesso' : 'non connesso'} />
        <h1>{state?.event_name || 'Photobooth'}</h1>
      </div>
      <div className="header-right">
        <Indicator label="Camera" ok={state?.hardware.camera ?? null} />
        <Indicator label="Stampa" ok={state?.hardware.printer ?? null} />
        <button className="icon-button" onClick={onOpenGallery} aria-label="Apri galleria scatti">
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path
              fill="currentColor"
              d="M4 4h7v7H4V4zm9 0h7v7h-7V4zM4 13h7v7H4v-7zm9 0h7v7h-7v-7z"
              opacity="0.9"
            />
          </svg>
        </button>
      </div>
    </header>
  )
}
