import { FormEvent, lazy, Suspense, useCallback, useState } from 'react'
import { canUseCamera, extractToken } from '../qr'

// the scanner and its decoder are only needed on this screen
const LiveQrScanner = lazy(() => import('./LiveQrScanner').then((m) => ({ default: m.LiveQrScanner })))

interface Props {
  invalid: boolean
  onSubmit: (token: string) => void
  onReset: () => void
}

export function TokenScreen({ invalid, onSubmit, onReset }: Props) {
  const [value, setValue] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const cameraAvailable = canUseCamera()

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSubmit(value.trim())
  }

  const handleQrText = useCallback(
    (text: string) => {
      setScanning(false)
      const token = extractToken(text)
      if (token) {
        navigator.vibrate?.(40)
        onSubmit(token)
      } else {
        setScanError('Il codice QR letto non è quello del photobooth.')
      }
    },
    [onSubmit],
  )

  return (
    <div className="token-screen">
      <img src="/icon.svg" alt="" width="72" height="72" />
      <h1>Photobooth</h1>
      <p className="muted">
        {invalid
          ? 'Il codice di accesso non è più valido: il motore potrebbe essere stato riavviato. Scansiona di nuovo il QR.'
          : 'Scansiona il codice QR mostrato nel terminale del photobooth, oppure inserisci il codice di accesso.'}
      </p>

      <button
        className="btn btn-print scan-button"
        disabled={!cameraAvailable}
        onClick={() => {
          setScanError(null)
          setScanning(true)
        }}
      >
        <span aria-hidden="true">📷</span> Scansiona QR
      </button>
      {!cameraAvailable && (
        <p className="muted small">
          La fotocamera è disponibile solo con HTTPS: avvia il motore senza l'opzione <code>--web-http</code>.
        </p>
      )}
      {scanError && <p className="panel-error">{scanError}</p>}

      <div className="divider">
        <span>oppure</span>
      </div>

      <form onSubmit={submit}>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Codice di accesso"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          aria-label="Codice di accesso"
        />
        <button className="btn btn-secondary" type="submit" disabled={!value.trim()}>
          Collegati
        </button>
      </form>
      {invalid && (
        <button className="link-button" onClick={onReset}>
          Dimentica il codice salvato
        </button>
      )}

      {scanning && (
        <Suspense fallback={<div className="scanner" />}>
          <LiveQrScanner onResult={handleQrText} onClose={() => setScanning(false)} />
        </Suspense>
      )}
    </div>
  )
}
