/**
 * The QR code printed by the engine contains the portal URL with the token (?t=...);
 * a bare token is accepted as well.
 */
export function extractToken(text: string): string | null {
  const value = text.trim()
  if (!value) return null
  try {
    return new URL(value).searchParams.get('t')
  } catch {
    return /^[\w-]+$/.test(value) ? value : null
  }
}

/** Browsers only expose the camera (getUserMedia) on HTTPS or localhost. */
export function canUseCamera(): boolean {
  return window.isSecureContext && !!navigator.mediaDevices?.getUserMedia
}
