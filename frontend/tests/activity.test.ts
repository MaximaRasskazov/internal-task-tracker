import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useComments } from '../src/features/task/useComments'
import { useHistory } from '../src/features/task/useHistory'
import { historyValue, tagColor } from '../src/features/task/history-format'
import { ApiError } from '../src/api/client'
const api = vi.hoisted(() => ({
  listComments: vi.fn(),
  postComment: vi.fn(),
  listHistory: vi.fn(),
}))
vi.mock('../src/api/activity', () => api)
const scopes: ReturnType<typeof effectScope>[] = []
function scoped<T>(fn: () => T): T {
  const scope = effectScope()
  scopes.push(scope)
  return scope.run(fn)!
}
const page = (items: unknown[] = [], total = items.length) => ({
  items,
  total,
  limit: 20,
  offset: 0,
})
beforeEach(() => {
  vi.resetAllMocks()
  api.listComments.mockResolvedValue(page())
})
afterEach(() => {
  scopes.forEach((s) => s.stop())
  scopes.length = 0
})
describe('comments', () => {
  it('rejects empty and oversized comments without a request', async () => {
    const c = scoped(() => useComments('t', vi.fn()))
    c.draft.value = '  '
    await c.send()
    c.draft.value = 'a'.repeat(5001)
    await c.send()
    expect(api.postComment).not.toHaveBeenCalled()
  })
  it('clears the draft only after confirmation and reports board revision', async () => {
    const saved = vi.fn()
    const c = scoped(() => useComments('t', saved))
    let resolve!: (value: unknown) => void
    api.postComment.mockReturnValue(
      new Promise((r) => {
        resolve = r
      }),
    )
    c.draft.value = ' Hello '
    const pending = c.send()
    expect(c.draft.value).toBe(' Hello ')
    await c.send()
    expect(api.postComment).toHaveBeenCalledTimes(1)
    resolve({ data: { id: 'c', text: 'Hello' }, board_revision: 7 })
    await pending
    expect(c.draft.value).toBe('')
    expect(saved).toHaveBeenCalledWith(7)
    expect(api.postComment).toHaveBeenCalledWith('t', 'Hello')
  })
  it('retains uncertain writes and requires a read and explicit retry', async () => {
    const c = scoped(() => useComments('t', vi.fn()))
    await c.load()
    c.draft.value = 'Keep me'
    api.postComment.mockRejectedValue(new ApiError(0, 'NETWORK', 'Offline'))
    await c.send()
    c.allowRetry()
    await c.send()
    expect(c.draft.value).toBe('Keep me')
    expect(c.uncertain.value).toBe(true)
    expect(api.postComment).toHaveBeenCalledTimes(1)
    await c.load()
    expect(c.uncertain.value).toBe(true)
    c.allowRetry()
    expect(c.uncertain.value).toBe(false)
  })
  it('retains drafts while paging and ignores older read responses', async () => {
    const c = scoped(() => useComments('t', vi.fn()))
    let resolve!: (value: unknown) => void
    api.listComments.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r
      }),
    )
    const first = c.load()
    c.draft.value = 'Draft'
    api.listComments.mockResolvedValueOnce(page([{ id: 'new' }], 21))
    await c.load(20)
    resolve(page([{ id: 'old' }]))
    await first
    expect(c.offset.value).toBe(20)
    expect(c.page.value?.items[0]?.id).toBe('new')
    expect(c.draft.value).toBe('Draft')
  })
  it('clears inaccessible comments and prevents writes after access loss', async () => {
    const c = scoped(() => useComments('t', vi.fn()))
    api.listComments.mockRejectedValue(new ApiError(403, 'FORBIDDEN', 'Forbidden'))
    await c.load()
    c.draft.value = 'Draft'
    await c.send()
    expect(c.page.value).toBeNull()
    expect(api.postComment).not.toHaveBeenCalled()
  })
})
describe('history', () => {
  it('keeps earlier events after a failed page and retries the same offset', async () => {
    const h = scoped(() => useHistory('t'))
    api.listHistory.mockResolvedValueOnce(page([{ id: 'a' }], 3))
    await h.load(true)
    api.listHistory.mockRejectedValueOnce(new ApiError(500, 'SERVER', 'Error'))
    await h.load()
    expect(h.items.value.map((i) => i.id)).toEqual(['a'])
    api.listHistory.mockResolvedValueOnce(page([{ id: 'a' }, { id: 'b' }], 3))
    await h.load()
    expect(api.listHistory.mock.calls[1]?.[1]).toBe(1)
    expect(api.listHistory.mock.calls[2]?.[1]).toBe(1)
    expect(h.items.value.map((i) => i.id)).toEqual(['a', 'b'])
    expect(h.hasMore.value).toBe(false)
  })
  it('refresh wins over an older pending page', async () => {
    const h = scoped(() => useHistory('t'))
    let resolve!: (value: unknown) => void
    api.listHistory.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r
      }),
    )
    const pending = h.load(true)
    api.listHistory.mockResolvedValueOnce(page([{ id: 'fresh' }]))
    await h.load(true)
    resolve(page([{ id: 'stale' }]))
    await pending
    expect(h.items.value.map((i) => i.id)).toEqual(['fresh'])
  })
  it('uses historical names and preserves zero, empty tags and calendar dates', () => {
    expect(historyValue({ id: 'u', name: 'Old name' }, 'assignee_id')).toBe('Old name')
    expect(historyValue([{ id: 'x', name: 'Old tag' }], 'tag_ids')).toBe('Old tag')
    expect(historyValue(0, 'story_points')).toBe('0')
    expect(historyValue([], 'tag_ids')).toBe('Нет')
    expect(historyValue('2026-11-04', 'deadline')).toBe('04.11.2026')
    expect(tagColor('url(unsafe)')).toBe('#64748B')
  })
})
