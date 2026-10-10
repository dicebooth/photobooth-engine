import { useState } from 'react'
import { clearToken, initToken, saveToken } from './api'
import { useEngineState } from './useEngineState'
import { Header } from './components/Header'
import { Preview } from './components/Preview'
import { ActionPanel } from './components/ActionPanel'
import { Gallery } from './components/Gallery'
import { TokenScreen } from './components/TokenScreen'

export default function App() {
  const [token, setToken] = useState<string | null>(() => initToken())
  const { state, connection } = useEngineState(token)
  const [galleryOpen, setGalleryOpen] = useState(false)

  if (!token || connection === 'unauthorized') {
    return (
      <TokenScreen
        invalid={connection === 'unauthorized'}
        onSubmit={(value) => {
          saveToken(value)
          setToken(value)
        }}
        onReset={() => {
          clearToken()
          setToken(null)
        }}
      />
    )
  }

  return (
    <div className="app">
      <Header state={state} connection={connection} onOpenGallery={() => setGalleryOpen(true)} />
      <main className="main">
        <Preview state={state} token={token} />
        <p className="status" aria-live="polite">
          {connection === 'offline' ? 'Connessione persa, riprovo...' : state?.status ?? 'Connessione...'}
        </p>
      </main>
      {state && <ActionPanel state={state} token={token} disabled={connection !== 'online'} />}
      {galleryOpen && state && (
        <Gallery token={token} limits={state.copies} refreshKey={state.version} onClose={() => setGalleryOpen(false)} />
      )}
    </div>
  )
}
