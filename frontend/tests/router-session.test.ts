import { afterEach, expect, it, vi } from 'vitest'
const state = vi.hoisted(() => ({
  user: { id: 'u', role: 'developer' } as { id: string; role: string } | null,
  restore: vi.fn(),
}))
vi.mock('../src/app/session', () => ({ useSession: () => state }))
import { router } from '../src/app/router'
router.addRoute({ path: '/navigation-test-a', component: { template: '<div/>' } })
router.addRoute({ path: '/navigation-test-b', component: { template: '<div/>' } })
afterEach(() => {
  state.restore.mockReset()
  state.user = { id: 'u', role: 'developer' }
})
it('keeps authenticated navigation available during a temporary API failure', async () => {
  state.restore.mockResolvedValue(undefined)
  await router.push('/navigation-test-a')
  state.restore.mockRejectedValue(new Error('offline'))
  await router.push('/navigation-test-b')
  expect(router.currentRoute.value.path).toBe('/navigation-test-b')
})
it('does not grant access without a known session during that same failure', async () => {
  state.user = null
  state.restore.mockRejectedValue(new Error('offline'))
  await router.push('/navigation-test-a')
  expect(router.currentRoute.value.path).toBe('/login')
  expect(router.currentRoute.value.query.returnTo).toBe('/navigation-test-a')
})
