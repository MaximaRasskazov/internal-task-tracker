import { expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import PrimeVue from 'primevue/config'
import ProjectsPage from '../src/features/projects/ProjectsPage.vue'
import { ApiError } from '../src/api/client'
const api = vi.hoisted(() => ({ listProjects: vi.fn(), createProject: vi.fn() }))
vi.mock('../src/api/projects', () => api)
vi.mock('../src/app/session', () => ({
  useSession: () => ({ canCreateProject: true, user: { role: 'pm' } }),
}))
it('retains the draft and retry block after closing and reopening project creation', async () => {
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe = vi.fn()
      unobserve = vi.fn()
      disconnect = vi.fn()
    },
  )
  api.listProjects.mockResolvedValue({ items: [], total: 0, limit: 12, offset: 0 })
  api.createProject.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Offline'))
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/projects', component: ProjectsPage }],
  })
  await router.push('/projects')
  await router.isReady()
  const w = mount(RouterView, {
    global: {
      plugins: [router, PrimeVue],
      stubs: { Dialog: { props: ['visible'], template: '<div v-if="visible"><slot/></div>' } },
    },
  })
  try {
    await flushPromises()
    await w
      .findAll('button')
      .find((b) => b.text() === 'Новый проект')!
      .trigger('click')
    await w.get('input[maxlength="100"]').setValue('Draft')
    await w.get('input[maxlength="8"]').setValue('TEAM')
    await w.get('form').trigger('submit')
    await flushPromises()
    await w
      .findAll('button')
      .find((b) => b.text() === 'Отмена')!
      .trigger('click')
    await w
      .findAll('button')
      .find((b) => b.text() === 'Новый проект')!
      .trigger('click')
    expect((w.get('input[maxlength="100"]').element as HTMLInputElement).value).toBe('Draft')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(api.createProject).toHaveBeenCalledTimes(1)
  } finally {
    w.unmount()
    vi.unstubAllGlobals()
  }
})
