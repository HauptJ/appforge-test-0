export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

let onUnauthorized: () => void = () => {}
export const setOnUnauthorized = (fn: () => void) => { onUnauthorized = fn }

function readCookie(name: string): string {
  const prefix = `${name}=`
  for (const part of document.cookie.split(';')) {
    const s = part.trim()
    if (s.startsWith(prefix)) return decodeURIComponent(s.slice(prefix.length))
  }
  return ''
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = readCookie('csrf_token')
    if (csrf) headers.set('X-CSRF-Token', csrf)
  }
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(new URL(`/api/v1${path}`, window.location.origin), {
    ...init,
    headers,
    credentials: 'same-origin',
  })
  if (res.status === 401) onUnauthorized()
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(
      res.status,
      body?.error?.code ?? 'error',
      body?.error?.message ?? res.statusText,
    )
  }
  return (res.status === 204 ? (undefined as T) : ((await res.json()) as T))
}

export interface SessionStatus {
  authenticated: boolean
  user: { email: string; name: string } | null
}

export interface HelloResponse {
  message: string
}

export const getStatus = () => api<SessionStatus>('/auth/status')
export const getHello = () => api<HelloResponse>('/hello')
export const logout = () =>
  fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRF-Token': readCookie('csrf_token') },
  })
