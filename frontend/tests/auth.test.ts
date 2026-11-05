import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import AuthPage from '../src/features/auth/AuthPage.vue'
import { useSession } from '../src/app/session'
const wrappers: ReturnType<typeof mount>[] = []
afterEach(() => {
  wrappers.forEach((w) => w.unmount())
  wrappers.length = 0
})
async function setup(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: AuthPage }],
  })
  await router.push(path)
  await router.isReady()
  const pinia = createPinia()
  const wrapper = mount(AuthPage, { global: { plugins: [pinia, router, PrimeVue] } })
  wrappers.push(wrapper)
  return { wrapper, router, store: useSession(pinia) }
}
describe('authentication form', () => {
  it('does not send mismatched registration passwords', async () => {
    const { wrapper, store } = await setup('/register')
    const register = vi.spyOn(store, 'register').mockResolvedValue({
      id: '1',
      name: 'A',
      email: 'a@example.test',
      role: 'developer',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    })
    await wrapper.get('#password').setValue('long-password-one')
    await wrapper.get('#confirmation').setValue('long-password-two')
    await wrapper.get('form').trigger('submit')
    expect(register).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toContain('Пароли не совпадают')
  })
  it('prevents duplicate login and redirects to the protected local route', async () => {
    const { wrapper, router, store } = await setup('/login?returnTo=/projects/123')
    let done!: () => void
    const login = vi.spyOn(store, 'login').mockReturnValue(
      new Promise<void>((resolve) => {
        done = resolve
      }),
    )
    await wrapper.get('input[type="email"]').setValue('a@example.test')
    await wrapper.get('#password').setValue('long-password-one')
    await wrapper.get('form').trigger('submit')
    await wrapper.get('form').trigger('submit')
    expect(login).toHaveBeenCalledTimes(1)
    expect(login).toHaveBeenCalledWith({ email: 'a@example.test', password: 'long-password-one' })
    done()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/projects/123')
  })
})
