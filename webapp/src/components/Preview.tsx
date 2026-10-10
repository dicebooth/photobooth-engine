import { useEffect, useState } from 'react'
import { api, EngineState } from '../api'

interface Props {
  state: EngineState | null
  token: string
}

export function Preview({ state, token }: Props) {
  const preview = state?.preview
  const src = preview?.available ? api.previewUrl(token, preview.id) : null
  // keep showing the previous image until the new one is decoded, avoiding a blank flash
  const [shownSrc, setShownSrc] = useState<string | null>(null)

  useEffect(() => {
    if (!src) {
      setShownSrc(null)
      return
    }
    const img = new Image()
    img.onload = () => setShownSrc(src)
    img.src = src
    return () => {
      img.onload = null
    }
  }, [src])

  const waiting = state?.phase === 'waiting_shot'

  return (
    <section className="preview">
      {shownSrc ? (
        <>
          <img src={shownSrc} alt="Anteprima scatto" />
          {preview?.kind && (
            <span className="badge">{preview.kind === 'framed' ? 'Con cornice' : 'Scatto originale'}</span>
          )}
        </>
      ) : (
        <div className={`preview-empty ${waiting ? 'pulse' : ''}`}>
          <svg viewBox="0 0 24 24" width="56" height="56" aria-hidden="true">
            <path
              fill="currentColor"
              d="M9 3 7.2 5H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.2L15 3H9zm3 15a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-2a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
            />
          </svg>
          <span>{waiting ? 'In attesa di scatto' : 'Nessuna foto da mostrare'}</span>
        </div>
      )}
    </section>
  )
}
