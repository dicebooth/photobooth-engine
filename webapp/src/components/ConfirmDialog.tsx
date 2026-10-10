interface Props {
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }: Props) {
  return (
    <div className="overlay" onClick={onCancel}>
      <div className="dialog" role="alertdialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        <p>{message}</p>
        <div className="panel-row">
          <button className="btn btn-secondary" onClick={onCancel}>
            Annulla
          </button>
          <button className="btn btn-print" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
