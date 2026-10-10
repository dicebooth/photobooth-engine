import { ReactNode, useEffect, useState } from 'react'
import { EngineState } from '../api'
import { ConfirmDialog } from './ConfirmDialog'

interface Props {
  limits: EngineState['copies']
  disabled: boolean
  onConfirm: (copies: number) => void
  /** optional button shown next to the print button (e.g. back / cancel) */
  secondaryAction?: ReactNode
  /** changing it resets the selection to the minimum */
  resetKey?: unknown
}

export const copiesLabel = (n: number) => `${n} ${n === 1 ? 'copia' : 'copie'}`

/**
 * Number of copies selector with a confirmation above the warning threshold,
 * shared by the print step of a new photo and by gallery reprints.
 */
export function CopiesPicker({ limits, disabled, onConfirm, secondaryAction, resetKey }: Props) {
  const { min, max, warn } = limits
  const [copies, setCopies] = useState(min)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    setCopies(min)
    setConfirming(false)
  }, [resetKey, min])

  return (
    <>
      <div className="stepper" role="group" aria-label="Numero di copie">
        <button
          className="stepper-btn"
          disabled={disabled || copies <= min}
          onClick={() => setCopies((c) => Math.max(min, c - 1))}
          aria-label="Una copia in meno"
        >
          −
        </button>
        <div className="stepper-value">
          <span className="stepper-number">{copies}</span>
          <span className="stepper-label">{copies === 1 ? 'copia' : 'copie'}</span>
        </div>
        <button
          className="stepper-btn"
          disabled={disabled || copies >= max}
          onClick={() => setCopies((c) => Math.min(max, c + 1))}
          aria-label="Una copia in più"
        >
          +
        </button>
      </div>
      <div className="panel-row">
        {secondaryAction}
        <button
          className="btn btn-print"
          disabled={disabled}
          onClick={() => (copies >= warn ? setConfirming(true) : onConfirm(copies))}
        >
          🖨 Stampa {copiesLabel(copies)}
        </button>
      </div>

      {confirming && (
        <ConfirmDialog
          title={`Stampare ${copies} copie?`}
          message={`Hai selezionato un numero elevato di copie (soglia di avviso: ${warn}).`}
          confirmLabel="Sì, stampa"
          onConfirm={() => {
            setConfirming(false)
            onConfirm(copies)
          }}
          onCancel={() => setConfirming(false)}
        />
      )}
    </>
  )
}
