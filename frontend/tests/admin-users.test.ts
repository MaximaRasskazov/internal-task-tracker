import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import PrimeVue from 'primevue/config'
import AdminUsersPage from '../src/features/settings/AdminUsersPage.vue'
const api = vi.hoisted(() => ({
  listUsers: vi.fn(),
  changeRole: vi.fn(),
  session: { user: { id: 'self', role: 'admin' } },
}))
vi.mock('../src/api/settings', () => ({ listUsers: api.listUsers, changeRole: api.changeRole }))
vi.mock('../src/app/session', () => ({ useSession: () => api.session }))
const wrappers: ReturnType<typeof mount>[] = []
beforeEach(() => {
  vi.resetAllMocks()
  api.session.user.role = 'admin'
  api.listUsers.mockResolvedValue({
    items: [
      { id: 'self', name: 'Self', email: 's@example.test', role: 'admin', is_active: true },
      { id: 'other', name: 'Other', email: 'o@example.test', role: 'developer', is_active: true },
    ],
    total: 2,
    limit: 20,
    offset: 0,
  })
})
afterEach(() => {
  wrappers.forEach((w) => w.unmount())
  wrappers.length = 0
  vi.restoreAllMocks()
})
async function setup() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/admin/users', component: AdminUsersPage }],
  })
  await router.push('/admin/users')
  await router.isReady()
  const w = mount(RouterView, { global: { plugins: [router, PrimeVue] } })
  wrappers.push(w)
  await flushPromises()
  return w
}
it('disables own role and respects cancellation for another user', async () => {
  const w = await setup()
  expect(w.get('[aria-label="Роль Self"]').attributes('disabled')).toBeDefined()
  vi.spyOn(window, 'confirm').mockReturnValue(false)
  await w.get('[aria-label="Роль Other"]').setValue('pm')
  await flushPromises()
  expect(api.changeRole).not.toHaveBeenCalled()
})
it('changes another role only after confirmation and refreshes the directory', async () => {
  const w = await setup()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  await w.get('[aria-label="Роль Other"]').setValue('pm')
  await flushPromises()
  expect(api.changeRole).toHaveBeenCalledWith('other', 'pm')
  expect(api.listUsers).toHaveBeenCalledTimes(2)
})
it('does not load the directory for non-admin users', async () => {
  api.session.user.role = 'developer'
  const w = await setup()
  expect(api.listUsers).not.toHaveBeenCalled()
  expect(w.text()).toContain('Доступ только для администратора')
})
