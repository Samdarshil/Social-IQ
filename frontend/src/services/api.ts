const TOKEN_KEY = 'socialiq.token'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t: string) => { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* storage blocked */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY) } catch { /* storage blocked */ } },
}

let onUnauthorized: (() => void) | null = null
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn }

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d[0] && typeof d[0] === 'object' && 'msg' in d[0]) return String((d[0] as { msg: string }).msg)
  }
  return fallback
}

export async function api<T>(path: string, opts: { method?: string; body?: unknown; params?: Record<string, string | number | undefined | null>; signal?: AbortSignal } = {}): Promise<T> {
  const qs = opts.params
    ? '?' + Object.entries(opts.params).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&')
    : ''
  const token = tokenStore.get()
  let res: Response
  try {
    res = await fetch(`/api${path}${qs === '?' ? '' : qs}`, {
      method: opts.method ?? 'GET',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: opts.signal,
    })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    throw new ApiError(0, 'Cannot reach the SocialIQ server. Is the backend running?')
  }
  let json: unknown = null
  try { json = await res.json() } catch { /* empty body */ }
  if (res.status === 401 && token) onUnauthorized?.()
  if (!res.ok) throw new ApiError(res.status, detailOf(json, `Request failed (${res.status})`))
  return json as T
}
