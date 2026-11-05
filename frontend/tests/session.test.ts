import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSession } from '../src/app/session'
import { ApiError } from '../src/api/client'
import type { Session } from '../src/api/types'
const mocked = vi.hoisted(() => ({ request: vi.fn(), configureSession: vi.fn() }))
vi.mock('../src/api/client', async (original) => ({
  ...(await original<typeof import('../src/api/client')>()),
  ...mocked,
}))
beforeEach(() => {
  setActivePinia(createPinia())
  mocked.request.mockReset()
  mocked.configureSession.mockReset()
})
describe('session restore', () => {
  it('shares one in-flight restore and does not resurrect a cleared session', async () => {
    let resolve!: (value: Session) => void
    mocked.request.mockReturnValue(
      new Promise<Session>((r) => {
        resolve = r
      }),
    )
    const store = useSession()
    const a = store.restore()
    const b = store.restore()
    expect(mocked.request).toHaveBeenCalledTimes(1)
    store.clear()
    resolve({
      user: {
        id: '1',
        name: 'Test',
        email: 'test@example.test',
        role: 'developer',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
      csrf_token: 'test',
      expires_at: '2026-01-02T00:00:00Z',
    })
    await Promise.all([a, b])
    expect(store.user).toBeNull()
  })
  it('allows retry after an unavailable server', async () => {
    mocked.request
      .mockRejectedValueOnce(new ApiError(503, 'UNAVAILABLE', 'Ошибка'))
      .mockRejectedValueOnce(new ApiError(401, 'AUTH_REQUIRED', 'Войдите'))
    const store = useSession()
    await expect(store.restore()).rejects.toBeInstanceOf(ApiError)
    expect(store.ready).toBe(false)
    await store.restore()
    expect(store.ready).toBe(true)
  })
})
