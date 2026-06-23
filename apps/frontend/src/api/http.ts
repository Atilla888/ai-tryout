export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Module-level token store — updated by App.tsx whenever the OIDC session changes. */
let accessToken: string | null = null

/** Stores the current access token so it can be injected into API requests. */
export function setAccessToken(token: string | null) {
  accessToken = token
}

/** Returns Authorization header if logged in, or an empty object for public endpoints. */
export function authHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}

/** Shared fetch wrapper for all API calls. Prepends the base URL, injects the
 * auth header, surfaces the API's `detail` message as the thrown error, and
 * transparently handles 204 No Content (e.g. delete). */
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers as Record<string, string>) },
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? `Request failed: ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
