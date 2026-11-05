import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, configureSession, request, setUnauthorizedHandler } from '../src/api/client'
afterEach(() => {
  vi.unstubAllGlobals()
  configureSession(null)
  setUnauthorizedHandler(() => {})
})
describe('HTTP contract', () => {
  it('sends cookies and CSRF on protected writes, handles 204', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetcher)
    configureSession('csrf-test')
    await expect(request('/auth/logout', { method: 'POST' })).resolves.toBeUndefined()
    const options = fetcher.mock.calls[0][1]
    expect(options.credentials).toBe('include')
    expect(options.headers.get('X-CSRF-Token')).toBe('csrf-test')
  })
  it('does not attach a stale CSRF to login', async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({}))
    vi.stubGlobal('fetch', fetcher)
    configureSession('old')
    await request('/auth/login', { method: 'POST', body: {}, public: true })
    expect(fetcher.mock.calls[0][1].headers.has('X-CSRF-Token')).toBe(false)
  })
  it('expires a protected session but leaves failed login to the form', async () => {
    const expired = vi.fn()
    setUnauthorizedHandler(expired)
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation(() =>
          Promise.resolve(
            Response.json(
              { error: { code: 'AUTH_REQUIRED', message: 'Войдите' } },
              { status: 401 },
            ),
          ),
        ),
    )
    await expect(request('/projects')).rejects.toMatchObject({ status: 401 })
    expect(expired).toHaveBeenCalledTimes(1)
    await expect(request('/auth/login', { public: true })).rejects.toBeInstanceOf(ApiError)
    expect(expired).toHaveBeenCalledTimes(1)
  })
  it('retains validation details and retry-after', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          Response.json(
            { error: { code: 'RATE_LIMITED', message: 'Подождите', details: [] } },
            { status: 429, headers: { 'Retry-After': '17' } },
          ),
        ),
    )
    await expect(request('/auth/login', { public: true })).rejects.toMatchObject({ retryAfter: 17 })
  })
  it('never retries a write with an unknown outcome', async () => {
    const fetcher = vi.fn().mockRejectedValue(new TypeError('connection lost'))
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/projects', { method: 'POST', body: {} })).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    })
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
})
