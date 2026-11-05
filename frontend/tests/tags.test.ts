import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import TagManager from '../src/features/tags/TagManager.vue'
import { ApiError } from '../src/api/client'
const api = vi.hoisted(() => ({
  listTags: vi.fn(),
  addTag: vi.fn(),
  patchTag: vi.fn(),
  deleteTag: vi.fn(),
}))
vi.mock('../src/api/activity', () => api)
const wrappers: ReturnType<typeof mount>[] = []
beforeEach(() => {
  vi.resetAllMocks()
  api.listTags.mockResolvedValue({
    items: [{ id: 'tag', name: 'Bug', color: '#FF0000' }],
    total: 1,
    offset: 0,
    limit: 20,
  })
})
afterEach(() => {
  wrappers.forEach((w) => w.unmount())
  wrappers.length = 0
  vi.restoreAllMocks()
})
async function setup(canManage = false) {
  const w = mount(TagManager, {
    props: { projectId: 'p', canManage },
    global: { plugins: [PrimeVue], stubs: { Dialog: { template: '<div><slot /></div>' } } },
  })
  wrappers.push(w)
  await flushPromises()
  return w
}
it('allows a member to create but hides rename and delete controls', async () => {
  const w = await setup()
  expect(w.find('[aria-label="Изменить тег Bug"]').exists()).toBe(false)
  expect(w.find('[aria-label="Удалить тег Bug"]').exists()).toBe(false)
  await w.get('input[maxlength="40"]').setValue(' New ')
  await w.get('form').trigger('submit')
  await flushPromises()
  expect(api.addTag).toHaveBeenCalledWith('p', { name: 'New', color: '#64748B' })
  expect(w.emitted('changed')).toHaveLength(1)
})
it('preserves the tag draft on duplicate-name failure', async () => {
  const w = await setup()
  api.addTag.mockRejectedValue(new ApiError(409, 'DUPLICATE_TAG', 'Тег уже существует'))
  await w.get('input[maxlength="40"]').setValue('Bug')
  await w.get('form').trigger('submit')
  await flushPromises()
  expect((w.get('input[maxlength="40"]').element as HTMLInputElement).value).toBe('Bug')
  expect(w.emitted('changed')).toBeUndefined()
})
it('shows the in-use explanation when deletion is rejected', async () => {
  const w = await setup(true)
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  api.deleteTag.mockRejectedValue(new ApiError(409, 'TAG_IN_USE', 'Тег используется'))
  await w.get('[aria-label="Удалить тег Bug"]').trigger('click')
  await flushPromises()
  expect(api.deleteTag).toHaveBeenCalledWith('tag')
  expect(w.text()).toContain('в том числе удалённых')
  expect(w.emitted('changed')).toBeUndefined()
})
it('blocks repeated creation after an uncertain server response', async () => {
  const w = await setup()
  api.addTag.mockRejectedValue(new ApiError(500, 'SERVER', 'Ошибка'))
  await w.get('input[maxlength="40"]').setValue('New')
  await w.get('form').trigger('submit')
  await flushPromises()
  await w.get('form').trigger('submit')
  await flushPromises()
  expect(api.addTag).toHaveBeenCalledTimes(1)
  expect(w.text()).toContain('Сервер мог сохранить изменение')
})

it('keeps an offline tag draft but blocks submission', async () => {
  const w = await setup(true)
  await w.get('input[maxlength="40"]').setValue('Draft')
  await w.setProps({ readOnly: true })
  await w.get('form').trigger('submit')
  await flushPromises()
  expect(api.addTag).not.toHaveBeenCalled()
  expect((w.get('input[maxlength="40"]').element as HTMLInputElement).value).toBe('Draft')
})
