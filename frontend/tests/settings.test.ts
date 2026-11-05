import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useSettingsMutation } from '../src/features/settings/useSettingsMutation'
import { ApiError } from '../src/api/client'
import {
  manages,
  shiftedColumns,
  orderColumns,
  addMember,
  changeOwner,
  changeRole,
  patchColumn,
} from '../src/api/settings'
import type { Snapshot, Task, User } from '../src/api/types'
const api = vi.hoisted(() => ({ request: vi.fn() }))
vi.mock('../src/api/client', async (original) => ({
  ...(await original<typeof import('../src/api/client')>()),
  request: api.request,
}))
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

const other: Task = { ...task, id: 'other', key: 'TEAM-2', position: 1 }
const third: Task = { ...task, id: 'third', key: 'TEAM-3', column_id: 'done', position: 0 }
function board(): Snapshot {
  return {
    board: {
      id: 'b',
      project_id: 'p',
      name: 'Board',
      revision: 1,
      created_at: task.created_at,
      updated_at: task.updated_at,
    },
    project: {
      id: 'p',
      key: 'TEAM',
      name: 'Project',
      description: '',
      timezone: 'UTC',
      owner_id: 'owner',
      board_count: 1,
      member_count: 1,
      created_at: task.created_at,
      updated_at: task.updated_at,
    },
    revision: 1,
    server_time: task.updated_at,
    members: [],
    tags: [],
    tasks: [task, other, third],
    columns: [
      { id: 'c', board_id: 'b', name: 'Todo', category: 'todo', position: 0 },
      { id: 'done', board_id: 'b', name: 'Done', category: 'done', position: 1 },
    ],
  }
}

const scopes: ReturnType<typeof effectScope>[] = []
beforeEach(() => vi.resetAllMocks())
afterEach(() => {
  scopes.forEach((s) => s.stop())
  scopes.length = 0
})
function setup(allowed = true) {
  const scope = effectScope()
  scopes.push(scope)
  const reload = vi.fn().mockResolvedValue(true)
  return { reload, mutation: scope.run(() => useSettingsMutation(() => allowed, reload))! }
}
const user: User = {
  id: 'u',
  name: 'User',
  email: 'u@example.test',
  created_at: '2026-11-05T00:00:00Z',
  role: 'developer',
  is_active: true,
}
it('allows project owners and administrators, not unrelated managers', () => {
  expect(manages(user, 'u')).toBe(true)
  expect(manages({ ...user, role: 'admin' }, 'someone')).toBe(true)
  expect(manages({ ...user, role: 'pm' }, 'someone')).toBe(false)
  expect(manages(null, 'u')).toBe(false)
})
it('blocks unauthorized writes before invoking the action', async () => {
  const { mutation } = setup(false),
    action = vi.fn()
  await mutation.run(action)
  expect(action).not.toHaveBeenCalled()
})
it('serializes writes and refreshes after confirmed success', async () => {
  const { mutation, reload } = setup()
  let resolve!: (v: unknown) => void
  const action = vi.fn().mockReturnValue(
      new Promise((r) => {
        resolve = r
      }),
    ),
    success = vi.fn()
  const pending = mutation.run(action, success)
  await mutation.run(action)
  expect(action).toHaveBeenCalledTimes(1)
  expect(success).not.toHaveBeenCalled()
  resolve({})
  await pending
  expect(success).toHaveBeenCalledTimes(1)
  expect(reload).toHaveBeenCalledTimes(1)
  expect(mutation.busy.value).toBe(false)
})
it.each([0, 500, 409])(
  'requires verification and explicit permission to retry uncertain/conflicting status %s',
  async (status) => {
    const { mutation, reload } = setup()
    const action = vi.fn().mockRejectedValue(new ApiError(status, 'VERSION_CONFLICT', 'Error')),
      success = vi.fn()
    await mutation.run(action, success)
    mutation.acknowledge()
    await mutation.run(action)
    expect(action).toHaveBeenCalledTimes(1)
    expect(success).not.toHaveBeenCalled()
    expect(mutation.blocked.value).toBe(true)
    reload.mockResolvedValueOnce(false)
    await mutation.verify()
    mutation.acknowledge()
    expect(mutation.blocked.value).toBe(true)
    await mutation.verify()
    expect(mutation.blocked.value).toBe(true)
    mutation.acknowledge()
    expect(mutation.blocked.value).toBe(false)
  },
)
it('keeps a refusal visible without treating a known nonempty result as uncertain', async () => {
  const { mutation } = setup()
  const failure = new ApiError(409, 'COLUMN_NOT_EMPTY', 'Колонка содержит задачи')
  const success = vi.fn()
  await mutation.run(vi.fn().mockRejectedValue(failure), success)
  expect(mutation.error.value).toBe(failure)
  expect(mutation.blocked.value).toBe(false)
  expect(success).not.toHaveBeenCalled()
})
it('blocks the next write when refresh fails after a confirmed mutation', async () => {
  const { mutation, reload } = setup()
  reload.mockResolvedValue(false)
  const action = vi.fn().mockResolvedValue({})
  expect(await mutation.run(action)).toBe(true)
  await mutation.run(action)
  expect(action).toHaveBeenCalledTimes(1)
  expect(mutation.notice.value).toContain('сохранено')
})
it('reorders all columns without modifying the snapshot', async () => {
  const snapshot = board(),
    ids = shiftedColumns(snapshot, 'done', -1)
  expect(ids).toEqual(['done', 'c'])
  expect(snapshot.columns[0]?.id).toBe('c')
  expect(shiftedColumns(snapshot, 'c', -1)).toBeNull()
  await orderColumns('b', ids!, 7)
  expect(api.request).toHaveBeenCalledWith('/boards/b/columns/order', {
    method: 'PUT',
    body: { column_ids: ['done', 'c'], expected_revision: 7 },
  })
})
it('uses membership email, owner ID, global role and name-only column contracts', async () => {
  await addMember('p', 'u@example.test')
  await changeOwner('p', 'u')
  await changeRole('u', 'pm')
  await patchColumn('c', 'Next')
  expect(api.request).toHaveBeenNthCalledWith(1, '/projects/p/members', {
    method: 'POST',
    body: { email: 'u@example.test' },
  })
  expect(api.request).toHaveBeenNthCalledWith(2, '/projects/p/owner', {
    method: 'PUT',
    body: { user_id: 'u' },
  })
  expect(api.request).toHaveBeenNthCalledWith(3, '/users/u/role', {
    method: 'PATCH',
    body: { role: 'pm' },
  })
  expect(api.request).toHaveBeenNthCalledWith(4, '/columns/c', {
    method: 'PATCH',
    body: { name: 'Next' },
  })
})
