import { useState } from 'react'
import { IDetectedBarcode, IScannerError, prepareZXingModule, Scanner } from '@yudiel/react-qr-scanner'
import zxingWasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url'

// iOS Safari has no native BarcodeDetector, so the scanner falls back to zxing-wasm.
// The .wasm file is bundled and served by the engine instead of the default CDN:
// the photobooth local network may have no internet access.
prepareZXingModule({
  overrides: {
    locateFile: (path: string, prefix: string) => (path.endsWith('.wasm') ? zxingWasmUrl : prefix + path),
  },
})

interface Props {
  onResult: (text: string) => void
  onClose: () => void
}

const ERROR_MESSAGES: Partial<Record<IScannerError['kind'], string>> = {
  'permission-denied': 'Accesso alla fotocamera negato. Consentilo dalle impostazioni del browser e riprova.',
  'no-camera': 'Nessuna fotocamera trovata su questo dispositivo.',
  'in-use': "La fotocamera è usata da un'altra app.",
  'insecure-context': 'La fotocamera richiede una connessione HTTPS.',
}

export function LiveQrScanner({ onResult, onClose }: Props) {
  const [error, setError] = useState<string | null>(null)

  const onScan = (codes: IDetectedBarcode[]) => {
    const text = codes[0]?.rawValue
    if (text) onResult(text)
  }

  return (
    <div className="scanner" role="dialog" aria-modal="true" aria-label="Scansione codice QR">
      <Scanner
        onScan={onScan}
        onError={(err) => setError(ERROR_MESSAGES[err.kind] ?? 'Impossibile avviare la fotocamera.')}
        formats={['qr_code']}
        constraints={{ facingMode: 'environment' }}
        components={{ finder: true, torch: true }}
        scanDelay={300}
        sound={false}
        classNames={{ container: 'scanner-view' }}
      />
      <p className="scanner-hint">{error ?? 'Inquadra il codice QR mostrato nel terminale'}</p>
      <button className="icon-button scanner-close" onClick={onClose} aria-label="Chiudi scanner">
        ✕
      </button>
    </div>
  )
}
