export type Phase = 'idle' | 'waiting_shot' | 'approval' | 'copies' | 'processing'

export interface EngineState {
  version: number
  phase: Phase
  status: string
  preview: { id: number; kind: 'shot' | 'framed' | null; available: boolean }
  copies: { min: number; max: number; warn: number }
  hardware: { camera: boolean | null; printer: boolean | null }
  event_name: string
}

export interface GalleryPhoto {
  name: string
  /** changes with the file: used to bust the browser cache */
  version: number
}

export class UnauthorizedError extends Error {}

const TOKEN_KEY = 'photobooth-token'

/**
 * The access token arrives in the QR code URL (?t=...): it is saved and removed from the address bar,
 * so that it is not leaked when the page is shared or bookmarked.
 */
export function initToken(): string | null {
  const url = new URL(window.location.href)
  const fromUrl = url.searchParams.get('t')
  if (fromUrl) {
    saveToken(fromUrl)
    url.searchParams.delete('t')
    window.history.replaceState(null, '', url.pathname + url.search + url.hash)
    return fromUrl
  }
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function saveToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // private mode: the token only lives in memory
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // ignore
  }
}

export function withToken(path: string, token: string): string {
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}t=${encodeURIComponent(token)}`
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-Photobooth-Token': token, ...init?.headers },
  })
  if (res.status === 401) throw new UnauthorizedError()
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`)
  return body as T
}

export const api = {
  state: (token: string) => request<EngineState>('/api/state', token),
  gallery: (token: string) => request<{ photos: GalleryPhoto[] }>('/api/gallery', token),
  /** prints are made in pairs: `pending` photos are waiting for the next one */
  reprint: (token: string, name: string, copies: number) =>
    request<{ ok: boolean; pending: number }>('/api/reprint', token, {
      method: 'POST',
      body: JSON.stringify({ name, copies }),
    }),
  approve: (token: string, accepted: boolean) =>
    request('/api/approval', token, { method: 'POST', body: JSON.stringify({ accepted }) }),
  copies: (token: string, copies: number) =>
    request('/api/copies', token, { method: 'POST', body: JSON.stringify({ copies }) }),
  /** undo the photo approval: back from the copies selection to the framed preview */
  back: (token: string) => request('/api/back', token, { method: 'POST', body: '{}' }),
  previewUrl: (token: string, id: number) => withToken(`/api/preview?id=${id}`, token),
  galleryUrl: (token: string, photo: GalleryPhoto, thumb: boolean) =>
    withToken(`/api/gallery/${encodeURIComponent(photo.name)}?v=${photo.version}${thumb ? '&thumb=1' : ''}`, token),
  eventsUrl: (token: string) => withToken('/api/events', token),
}
