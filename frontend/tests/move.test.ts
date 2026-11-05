import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import type { Snapshot, Task } from '../src/api/types'
import { useTaskMove, orderedTasks, previewTasks } from '../src/features/board/useTaskMove'
import KanbanBoard from '../src/features/board/KanbanBoard.vue'
import MoveTaskDialog from '../src/features/board/MoveTaskDialog.vue'
import { ApiError } from '../src/api/client'
const api = vi.hoisted(() => ({ moveTask: vi.fn() }))
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
const wrappers: ReturnType<typeof mount>[] = []
beforeEach(() => {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  )
  vi.resetAllMocks()
  api.moveTask.mockResolvedValue({
    data: { ...task, version: 2 },
    board_id: 'b',
    board_revision: 2,
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  scopes.forEach((s) => s.stop())
  scopes.length = 0
  wrappers.forEach((w) => w.unmount())
  wrappers.length = 0
})
function setup(writable = true) {
  const snapshot = board()
  const refresh = vi.fn<(r?: number) => Promise<number | undefined>>().mockResolvedValue(2)
  const scope = effectScope()
  scopes.push(scope)
  const mover = scope.run(() =>
    useTaskMove(
      () => snapshot,
      () => writable,
      refresh,
    ),
  )!
  return { mover, snapshot, refresh }
}
describe('task placement', () => {
  it('sends the captured version and anchor ID, not a visible index', async () => {
    const { mover, refresh } = setup()
    await mover.move(task, 'done', 'third')
    expect(api.moveTask).toHaveBeenCalledWith('t', {
      column_id: 'done',
      before_task_id: 'third',
      expected_version: 1,
    })
    expect(refresh).toHaveBeenCalledWith(2)
  })
  it('previews the order without changing a snapshot and ignores stale overlays', () => {
    const snapshot = board()
    const move = { task, columnId: 'done', beforeId: 'third' }
    const preview = previewTasks(snapshot.tasks, move)
    expect(orderedTasks(preview, 'done').map((t) => t.id)).toEqual(['t', 'third'])
    expect(snapshot.tasks[0]?.column_id).toBe('c')
    const newer = [{ ...task, version: 2 }, other, third]
    expect(previewTasks(newer, move)).toBe(newer)
  })
  it('handles end placement and reorder within the same column', async () => {
    const { mover } = setup()
    expect(
      orderedTasks(previewTasks(board().tasks, { task, columnId: 'c', beforeId: null }), 'c').map(
        (t) => t.id,
      ),
    ).toEqual(['other', 't'])
    await mover.move(task, 'c', null)
    expect(api.moveTask).toHaveBeenCalledWith('t', {
      column_id: 'c',
      before_task_id: null,
      expected_version: 1,
    })
  })
  it('does not send no-ops, self anchors, invalid anchors or offline writes', async () => {
    const { mover } = setup()
    await mover.move(task, 'c', 'other')
    await mover.move(task, 'c', 't')
    await mover.move(task, 'done', 'missing')
    await setup(false).mover.move(task, 'done', null)
    expect(api.moveTask).not.toHaveBeenCalled()
  })
  it('allows only one pending operation and keeps its visual preview', async () => {
    let resolve!: (v: unknown) => void
    api.moveTask.mockReturnValue(
      new Promise((r) => {
        resolve = r
      }),
    )
    const { mover } = setup()
    const first = mover.move(task, 'done', null)
    await mover.move(other, 'done', null)
    expect(api.moveTask).toHaveBeenCalledTimes(1)
    expect(mover.pending.value?.task.id).toBe('t')
    resolve({ data: task, board_revision: 2 })
    await first
    expect(mover.pending.value).toBeNull()
    expect(mover.busy.value).toBe(false)
  })
  it.each([0, 409, 500])(
    'rolls back only the preview and blocks automatic retry after %s',
    async (status) => {
      const { mover, snapshot } = setup()
      api.moveTask.mockRejectedValue(new ApiError(status, 'POSITION_CONFLICT', 'Conflict'))
      await mover.move(task, 'done', null)
      expect(mover.pending.value).toBeNull()
      expect(snapshot.tasks[0]).toEqual(task)
      expect(mover.blocked.value).toBe(true)
      await mover.move(task, 'done', null)
      expect(api.moveTask).toHaveBeenCalledTimes(1)
      expect(mover.verified.value).toBe(true)
      mover.acknowledge()
      expect(mover.blocked.value).toBe(false)
    },
  )
  it('requires a sufficiently new snapshot after successful move before unlocking', async () => {
    const { mover, refresh } = setup()
    refresh.mockResolvedValue(1)
    await mover.move(task, 'done', null)
    mover.acknowledge()
    expect(mover.blocked.value).toBe(true)
    refresh.mockResolvedValue(2)
    await mover.verify()
    mover.acknowledge()
    expect(mover.blocked.value).toBe(false)
    expect(api.moveTask).toHaveBeenCalledTimes(1)
  })
  it('does not treat a failed refresh as verification', async () => {
    const { mover, refresh } = setup()
    refresh.mockRejectedValue(new Error('offline'))
    await mover.move(task, 'done', null)
    expect(mover.verified.value).toBe(false)
    expect(mover.blocked.value).toBe(true)
    expect(api.moveTask).toHaveBeenCalledTimes(1)
  })
})
describe('accessible move controls', () => {
  it('offers a separate move button without opening the task', async () => {
    const w = mount(KanbanBoard, {
      props: { board: board(), disabled: false, pending: null },
      global: { plugins: [PrimeVue] },
    })
    wrappers.push(w)
    await w.get('[aria-label="Переместить TEAM-1"]').trigger('click')
    expect(w.emitted('chooseMove')?.[0]?.[0]).toEqual(task)
    expect(w.emitted('open')).toBeUndefined()
  })
  it('submits a selectable placement without drag and blocks it offline', async () => {
    const w = mount(MoveTaskDialog, {
      props: { board: board(), task, disabled: false, busy: false },
      global: { plugins: [PrimeVue], stubs: { Dialog: { template: '<div><slot/></div>' } } },
    })
    wrappers.push(w)
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(w.emitted('move')?.[0]).toEqual([task, 'c', null])
    await w.setProps({ disabled: true })
    await w.get('form').trigger('submit')
    expect(w.emitted('move')).toHaveLength(1)
  })
})

it('maps a native drop to the target column end and cancels external drops', async () => {
  const w = mount(KanbanBoard, {
    props: { board: board(), disabled: false, pending: null },
    global: { plugins: [PrimeVue] },
  })
  wrappers.push(w)
  await w.findAll('.drop-end')[1]!.trigger('drop')
  expect(w.emitted('move')).toBeUndefined()
  const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }
  await w.findAll('article')[0]!.trigger('dragstart', { dataTransfer })
  await w.findAll('.drop-end')[1]!.trigger('dragover', { dataTransfer })
  await w.findAll('.drop-end')[1]!.trigger('drop', { dataTransfer })
  expect(w.emitted('move')?.[0]).toEqual([task, 'done', null])
  expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', 't')
})

it('keeps hidden cards in the source snapshot while moving before a visible anchor', async () => {
  const snapshot = board()
  snapshot.tasks = [task, { ...other, column_id: 'done', position: 0 }, { ...third, position: 1 }]
  const w = mount(KanbanBoard, {
    props: { board: snapshot, disabled: false, pending: null, visibleIds: new Set(['t', 'third']) },
    global: { plugins: [PrimeVue] },
  })
  wrappers.push(w)
  expect(w.findAll('article')).toHaveLength(2)
  const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }
  await w.findAll('article')[0]!.trigger('dragstart', { dataTransfer })
  await w.findAll('article')[1]!.trigger('drop', { dataTransfer })
  expect(w.emitted('move')?.[0]).toEqual([task, 'done', 'third'])
  const preview = previewTasks(snapshot.tasks, { task, columnId: 'done', beforeId: 'third' })
  expect(orderedTasks(preview, 'done').map((t) => t.id)).toEqual(['other', 't', 'third'])
  expect(snapshot.tasks).toHaveLength(3)
})
it('retains all drop columns when the filter has no matching cards', () => {
  const w = mount(KanbanBoard, {
    props: { board: board(), disabled: false, pending: null, visibleIds: new Set<string>() },
    global: { plugins: [PrimeVue] },
  })
  wrappers.push(w)
  expect(w.findAll('article')).toHaveLength(0)
  expect(w.findAll('.drop-end')).toHaveLength(2)
})
