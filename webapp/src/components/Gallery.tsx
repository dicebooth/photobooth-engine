import { useEffect, useState } from 'react'
import { api, EngineState, GalleryPhoto } from '../api'
import { vibrate } from './ActionPanel'
import { copiesLabel, CopiesPicker } from './CopiesPicker'

interface Props {
  token: string
  limits: EngineState['copies']
  refreshKey: number
  onClose: () => void
}

type ReprintStatus = { kind: 'sending' } | { kind: 'done'; message: string } | { kind: 'error'; message: string }

export function Gallery({ token, limits, refreshKey, onClose }: Props) {
  const [photos, setPhotos] = useState<GalleryPhoto[] | null>(null)
  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => {
    api
      .gallery(token)
      .then((res) => setPhotos(res.photos))
      .catch(() => setPhotos([]))
  }, [token, refreshKey])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') (selected !== null ? setSelected(null) : onClose())
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, onClose])

  return (
    <div className="sheet" role="dialog" aria-modal="true" aria-label="Galleria scatti">
      <div className="sheet-header">
        <h2>
          Galleria scatti {photos && <span className="muted">· {photos.length}</span>}
        </h2>
        <button className="icon-button" onClick={onClose} aria-label="Chiudi galleria">
          ✕
        </button>
      </div>

      <div className="sheet-body">
        {photos === null && <p className="muted center">Caricamento...</p>}
        {photos?.length === 0 && <p className="muted center">Nessuno scatto ancora.</p>}

        <div className="grid">
          {photos?.map((photo, i) => (
            <button key={photo.name} className="thumb" onClick={() => setSelected(i)} aria-label={`Apri ${photo.name}`}>
              <img src={api.galleryUrl(token, photo, true)} alt="" loading="lazy" />
            </button>
          ))}
        </div>
      </div>

      {photos && selected !== null && photos[selected] && (
        <PhotoViewer
          token={token}
          limits={limits}
          photo={photos[selected]}
          hasNewer={selected > 0}
          hasOlder={selected < photos.length - 1}
          onNavigate={(delta) => setSelected(selected + delta)}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}

interface ViewerProps {
  token: string
  limits: EngineState['copies']
  photo: GalleryPhoto
  hasNewer: boolean
  hasOlder: boolean
  onNavigate: (delta: number) => void
  onClose: () => void
}

function PhotoViewer({ token, limits, photo, hasNewer, hasOlder, onNavigate, onClose }: ViewerProps) {
  const [reprinting, setReprinting] = useState(false)
  const [status, setStatus] = useState<ReprintStatus | null>(null)

  // moving to another photo closes the reprint panel
  useEffect(() => {
    setReprinting(false)
    setStatus(null)
  }, [photo.name])

  const reprint = async (copies: number) => {
    vibrate()
    setStatus({ kind: 'sending' })
    try {
      const res = await api.reprint(token, photo.name, copies)
      setReprinting(false)
      setStatus({
        kind: 'done',
        message:
          res.pending > 0
            ? `${copiesLabel(copies)} in coda: le foto si stampano a coppie, partirà con la prossima.`
            : `${copiesLabel(copies)} in stampa.`,
      })
    } catch (err) {
      setStatus({ kind: 'error', message: err instanceof Error ? err.message : 'Errore inatteso' })
    }
  }

  return (
    <div className="lightbox">
      <div className="lightbox-top">
        <span className="muted lightbox-name">{photo.name}</span>
        <button className="icon-button" onClick={onClose} aria-label="Chiudi foto">
          ✕
        </button>
      </div>

      <div className="lightbox-image">
        <button className="icon-button nav" disabled={!hasNewer} onClick={() => onNavigate(-1)} aria-label="Foto più recente">
          ‹
        </button>
        <img src={api.galleryUrl(token, photo, false)} alt={photo.name} />
        <button className="icon-button nav" disabled={!hasOlder} onClick={() => onNavigate(1)} aria-label="Foto precedente">
          ›
        </button>
      </div>

      <div className="panel lightbox-panel">
        {status?.kind === 'done' && <p className="panel-success">{status.message}</p>}
        {status?.kind === 'error' && <p className="panel-error">{status.message}</p>}

        {reprinting ? (
          <CopiesPicker
            limits={limits}
            disabled={status?.kind === 'sending'}
            resetKey={photo.name}
            onConfirm={reprint}
            secondaryAction={
              <button className="btn btn-secondary btn-back" onClick={() => setReprinting(false)}>
                Annulla
              </button>
            }
          />
        ) : (
          <button
            className="btn btn-print"
            onClick={() => {
              setStatus(null)
              setReprinting(true)
            }}
          >
            🖨 Ristampa
          </button>
        )}
      </div>
    </div>
  )
}
