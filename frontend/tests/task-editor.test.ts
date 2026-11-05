import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { flushPromises } from '@vue/test-utils'
import type { Task } from '../src/api/types'
import { ApiError } from '../src/api/client'
import { useTaskEditor } from '../src/features/task/useTaskEditor'
import { changes, draftFrom, canDelete } from '../src/features/task/draft'
const api = vi.hoisted(() => ({
  readTask: vi.fn(),
  updateTask: vi.fn(),
  addTask: vi.fn(),
  removeTask: vi.fn(),
}))
vi.mock('../src/api/tasks', () => api)
const task: Task = {
  id: 't',
  project_id: 'p',
  board_id: 'b',
  number: 1,
  key: 'TEAM-1',
  title: 'Исходная',
  description: 'Описание',
  column_id: 'c',
  position: 0,
  priority: 'medium',
  author_id: 'author',
  author: { id: 'author', name: 'Автор' },
  assignee_id: 'dev',
  assignee: { id: 'dev', name: 'Разработчик' },
  assignee_is_project_member: true,
  deadline: '2026-11-12',
  story_points: 3,
  tag_ids: ['one', 'two'],
  version: 1,
  is_completed: false,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
}
const response = (value: Task) => ({ data: value, board_id: 'b', board_revision: value.version })
const scopes: ReturnType<typeof effectScope>[] = []
function setup(id: string | undefined, saved = vi.fn()) {
  const scope = effectScope()
  scopes.push(scope)
  const editor = scope.run(() => useTaskEditor('b', id, 'c', saved))!
  return { editor, saved }
}
beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset())
  api.readTask.mockResolvedValue(response(task))
})
afterEach(() => {
  scopes.forEach((s) => s.stop())
  scopes.length = 0
})
describe('task patch', () => {
  it('omits unchanged fields and preserves explicit null, empty string, zero, and empty tags', () => {
    const base = draftFrom(task)
    const draft = {
      ...base,
      description: '',
      assignee_id: null,
      deadline: null,
      story_points: 0,
      tag_ids: [],
    }
    expect(changes(base, draft)).toEqual({
      description: '',
      assignee_id: null,
      deadline: null,
      story_points: 0,
      tag_ids: [],
    })
  })
  it('ignores tag display order and does not shift a calendar date', () => {
    expect(changes(draftFrom(task), { ...draftFrom(task), tag_ids: ['two', 'one'] })).toEqual({})
    expect(draftFrom(task).deadline).toBe('2026-11-12')
  })
  it('allows deletion only for admin, project owner or author', () => {
    expect(canDelete(task, 'other', 'developer', 'owner')).toBe(false)
    expect(canDelete(task, 'author', 'developer', 'owner')).toBe(true)
    expect(canDelete(task, 'owner', 'developer', 'owner')).toBe(true)
    expect(canDelete(task, 'other', 'admin', 'owner')).toBe(true)
  })
})
describe('task operations', () => {
  it('sends only changed fields with the loaded version', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.draft.value.title = 'Новое'
    api.updateTask.mockResolvedValue(response({ ...task, title: 'Новое', version: 2 }))
    await editor.save()
    expect(api.updateTask).toHaveBeenCalledWith('t', { title: 'Новое', expected_version: 1 })
    expect(editor.dirty.value).toBe(false)
  })
  it('keeps the draft on 409 and rebases only edited fields after explicit choice', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.draft.value.title = 'Мой текст'
    api.updateTask.mockRejectedValue(new ApiError(409, 'VERSION_CONFLICT', 'Конфликт'))
    api.readTask.mockResolvedValue(
      response({ ...task, version: 2, description: 'Изменение коллеги' }),
    )
    await editor.save()
    expect(editor.draft.value.title).toBe('Мой текст')
    expect(editor.blocked.value).toBe(true)
    await editor.save()
    expect(api.updateTask).toHaveBeenCalledTimes(1)
    editor.resolveConflict(true)
    expect(editor.draft.value.description).toBe('Изменение коллеги')
    api.updateTask.mockResolvedValue(
      response({ ...task, title: 'Мой текст', description: 'Изменение коллеги', version: 3 }),
    )
    await editor.save()
    expect(api.updateTask).toHaveBeenLastCalledWith('t', {
      title: 'Мой текст',
      expected_version: 2,
    })
  })
  it('can discard the local draft after a conflict', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.draft.value.title = 'Черновик'
    api.updateTask.mockRejectedValue(new ApiError(409, 'VERSION_CONFLICT', 'Конфликт'))
    api.readTask.mockResolvedValue(response({ ...task, title: 'Сервер', version: 2 }))
    await editor.save()
    editor.resolveConflict(false)
    expect(editor.draft.value.title).toBe('Сервер')
    expect(editor.dirty.value).toBe(false)
  })
  it('does not retry creation after an uncertain network result', async () => {
    const { editor } = setup(undefined)
    editor.draft.value.title = 'Создать'
    api.addTask.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Ошибка сети'))
    await editor.save()
    await editor.save()
    expect(api.addTask).toHaveBeenCalledTimes(1)
    expect(editor.draft.value.title).toBe('Создать')
  })
  it('keeps entered text and field errors on validation failure', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.draft.value.title = 'Мой текст'
    api.updateTask.mockRejectedValue(
      new ApiError(422, 'VALIDATION_ERROR', 'Ошибка', [
        { field: 'title', message: 'Проверьте название' },
      ]),
    )
    await editor.save()
    expect(editor.draft.value.title).toBe('Мой текст')
    expect(editor.blocked.value).toBe(false)
    expect(editor.error.value).toMatchObject({ status: 422 })
  })
  it('releases the navigation lock before reporting successful deletion', async () => {
    const { editor, saved } = setup('t')
    await flushPromises()
    api.removeTask.mockResolvedValue({ data: null, board_id: 'b', board_revision: 2 })
    saved.mockImplementation(() => expect(editor.busy.value).toBe(false))
    await editor.remove()
    expect(api.removeTask).toHaveBeenCalledWith('t', 1)
    expect(saved).toHaveBeenCalledWith(2)
  })
})

describe('creation navigation', () => {
  it('is clean after creating in a different column so navigation does not prompt again', async () => {
    const { editor, saved } = setup(undefined)
    editor.draft.value.title = 'Новая'
    editor.columnId.value = 'other'
    api.addTask.mockResolvedValue(response({ ...task, title: 'Новая', column_id: 'other' }))
    saved.mockImplementation(() => {
      expect(editor.busy.value).toBe(false)
      expect(editor.dirty.value).toBe(false)
    })
    await editor.save()
    expect(saved).toHaveBeenCalledTimes(1)
  })
  it('allows only one pending write', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.draft.value.title = 'Правка'
    let finish!: (value: ReturnType<typeof response>) => void
    api.updateTask.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve
      }),
    )
    const pending = editor.save()
    await editor.save()
    expect(api.updateTask).toHaveBeenCalledTimes(1)
    finish(response({ ...task, title: 'Правка', version: 2 }))
    await pending
  })
})

describe('remote task changes', () => {
  it('updates a clean form from a newer snapshot', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.syncSnapshot({ ...task, version: 2, title: 'Remote' })
    expect(editor.draft.value.title).toBe('Remote')
    expect(editor.dirty.value).toBe(false)
    editor.syncSnapshot(task)
    expect(editor.draft.value.title).toBe('Remote')
  })
  it('preserves local edits and requires explicit reconciliation', async () => {
    const { editor } = setup('t')
    await flushPromises()
    editor.draft.value.title = 'Local draft'
    editor.syncSnapshot({ ...task, version: 2, description: 'Remote description' })
    expect(editor.draft.value.title).toBe('Local draft')
    expect(editor.blocked.value).toBe(true)
    expect(editor.latest.value?.version).toBe(2)
    editor.resolveConflict(true)
    expect(editor.draft.value.title).toBe('Local draft')
    expect(editor.draft.value.description).toBe('Remote description')
    expect(editor.task.value?.version).toBe(2)
  })
})
