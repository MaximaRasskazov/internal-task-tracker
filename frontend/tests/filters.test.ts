import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { effectScope, ref, nextTick } from 'vue'
import { flushPromises } from '@vue/test-utils'
import {
  emptyFilters,
  readFilters,
  filterParams,
  filterQuery,
  filterError,
} from '../src/features/board/filters'
import { useFilteredTasks } from '../src/features/board/useFilteredTasks'
const api = vi.hoisted(() => ({ request: vi.fn() }))
vi.mock('../src/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../src/api/client')>()),
  request: api.request,
}))
const scopes: ReturnType<typeof effectScope>[] = []
beforeEach(() => {
  api.request.mockReset()
})
afterEach(() => {
  scopes.forEach((s) => s.stop())
  scopes.length = 0
})
function setup() {
  const filters = ref(emptyFilters()),
    revision = ref<number | undefined>(1),
    refresh = vi.fn().mockResolvedValue(undefined)
  const scope = effectScope()
  scopes.push(scope)
  const result = scope.run(() =>
    useFilteredTasks(
      'b',
      () => filters.value,
      () => revision.value,
      refresh,
    ),
  )!
  return { filters, revision, refresh, result }
}
it('round-trips repeated criteria and preserves task links when resetting', () => {
  const query = {
    task: 't',
    q: 'A & B',
    tag_ids: ['a', 'b', 'a'],
    priority: ['low', 'high'],
    column_ids: ['c', 'd'],
    assignee_id: 'unassigned',
    deadline_from: '2026-11-01',
    deadline_to: '2026-11-05',
  }
  const filters = readFilters(query),
    params = filterParams(filters)
  expect(params.getAll('tag_ids')).toEqual(['a', 'b'])
  expect(params.getAll('priority')).toEqual(['low', 'high'])
  expect(params.get('q')).toBe('A & B')
  expect(params.get('assignee_id')).toBe('unassigned')
  expect(filterQuery(query, emptyFilters())).toEqual({ task: 't' })
  expect(readFilters(filterQuery({}, filters) as typeof query)).toEqual(filters)
})
it('accepts inclusive date bounds, rejects impossible/reversed dates and invalid priorities', () => {
  expect(
    filterError({ ...emptyFilters(), deadline_from: '2026-11-05', deadline_to: '2026-11-05' }),
  ).toBe('')
  expect(filterError({ ...emptyFilters(), deadline_from: '2026-02-30' })).not.toBe('')
  expect(
    filterError({ ...emptyFilters(), deadline_from: '2026-11-06', deadline_to: '2026-11-05' }),
  ).not.toBe('')
  expect(filterError({ ...emptyFilters(), priority: ['invalid'] })).not.toBe('')
  expect(filterError({ ...emptyFilters(), q: 'x'.repeat(101) })).not.toBe('')
})
it('does not request a filtered list without criteria', async () => {
  const { result } = setup()
  await flushPromises()
  expect(api.request).not.toHaveBeenCalled()
  expect(result.ids.value).toBeNull()
  expect(result.ready.value).toBe(true)
})
it('sends combined filters in one GET and accepts a matching snapshot revision', async () => {
  api.request.mockResolvedValue({ items: [{ id: 'match' }], board_revision: 1, total: 1 })
  const { filters, result } = setup()
  filters.value = {
    ...emptyFilters(),
    tag_ids: ['a', 'b'],
    priority: ['high'],
    assignee_id: 'unassigned',
  }
  await flushPromises()
  const url = String(api.request.mock.calls[0]?.[0])
  const params = new URLSearchParams(url.split('?')[1])
  expect(params.getAll('tag_ids')).toEqual(['a', 'b'])
  expect(params.get('priority')).toBe('high')
  expect(params.get('assignee_id')).toBe('unassigned')
  expect(result.ids.value?.has('match')).toBe(true)
  expect(result.ready.value).toBe(true)
})
it('ignores a late response for an older search', async () => {
  let resolve!: (v: unknown) => void
  api.request
    .mockReturnValueOnce(
      new Promise((r) => {
        resolve = r
      }),
    )
    .mockResolvedValueOnce({ items: [{ id: 'new' }], board_revision: 1, total: 1 })
  const { filters, result } = setup()
  filters.value = { ...emptyFilters(), q: 'old' }
  await nextTick()
  filters.value = { ...emptyFilters(), q: 'new' }
  await flushPromises()
  resolve({ items: [{ id: 'old' }], board_revision: 1, total: 1 })
  await flushPromises()
  expect([...result.ids.value!]).toEqual(['new'])
})
it.each([0, 2])(
  'rejects selection from revision %s when the board is revision 1',
  async (revision) => {
    api.request.mockResolvedValue({ items: [{ id: 'stale' }], board_revision: revision, total: 1 })
    const { filters, result, refresh } = setup()
    filters.value = { ...emptyFilters(), q: 'x' }
    await flushPromises()
    expect(result.ready.value).toBe(false)
    expect(result.ids.value?.size).toBe(0)
    expect(refresh).toHaveBeenCalledTimes(1)
  },
)
it('refreshes selection after realtime revision changes', async () => {
  api.request
    .mockResolvedValueOnce({ items: [{ id: 'old' }], board_revision: 1, total: 1 })
    .mockResolvedValueOnce({ items: [], board_revision: 2, total: 0 })
  const { filters, result, revision } = setup()
  filters.value = { ...emptyFilters(), column_ids: ['c'] }
  await flushPromises()
  revision.value = 2
  await flushPromises()
  expect(api.request).toHaveBeenCalledTimes(2)
  expect(result.ready.value).toBe(true)
  expect(result.ids.value?.size).toBe(0)
})
it('reset cancels an outstanding search and exposes the full snapshot', async () => {
  let resolve!: (v: unknown) => void
  api.request.mockReturnValue(
    new Promise((r) => {
      resolve = r
    }),
  )
  const { filters, result } = setup()
  filters.value = { ...emptyFilters(), q: 'x' }
  await nextTick()
  filters.value = emptyFilters()
  await nextTick()
  resolve({ items: [], board_revision: 1, total: 0 })
  await flushPromises()
  expect(result.ids.value).toBeNull()
  expect(result.ready.value).toBe(true)
})
it('invalid URL dates produce an actionable error without a request', async () => {
  const { filters, result } = setup()
  filters.value = { ...emptyFilters(), deadline_to: 'invalid' }
  await flushPromises()
  expect(result.error.value).not.toBe('')
  expect(api.request).not.toHaveBeenCalled()
})
