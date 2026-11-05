import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import type { Snapshot, Task, TaskMove } from '../../api/types'
import { moveTask } from '../../api/tasks'
import { ApiError } from '../../api/client'
export type Placement = { task: Task; columnId: string; beforeId: string | null }
export function orderedTasks(tasks: Task[], columnId: string) {
  return tasks
    .filter((t) => t.column_id === columnId)
    .sort((a, b) => a.position - b.position || a.id.localeCompare(b.id))
}
/** A display-only overlay: server snapshots are never rolled back by an old request. */
export function previewTasks(tasks: Task[], move: Placement | null): Task[] {
  if (!move) return tasks
  const current = tasks.find((t) => t.id === move.task.id)
  if (!current || current.version > move.task.version) return tasks
  const rest = tasks.filter((t) => t.id !== current.id)
  const target = orderedTasks(rest, move.columnId)
  const at =
    move.beforeId === null ? target.length : target.findIndex((t) => t.id === move.beforeId)
  if (at < 0) return tasks
  target.splice(at, 0, { ...current, column_id: move.columnId })
  const positions = new Map(target.map((t, i) => [t.id, i]))
  return [
    ...rest.filter((t) => t.column_id !== move.columnId),
    ...target.map((t) => ({ ...t, position: positions.get(t.id)! })),
  ]
}
export function useTaskMove(
  snapshot: () => Snapshot | null,
  writable: () => boolean,
  refresh: (revision?: number) => Promise<number | undefined>,
) {
  const busy = ref(false)
  const blocked = ref(false)
  const verified = ref(false)
  const pending = shallowRef<Placement | null>(null)
  const error = shallowRef<unknown>(null)
  const notice = ref('')
  let requiredRevision = 0
  let active = true
  onScopeDispose(() => {
    active = false
  })
  async function verify() {
    verified.value = false
    try {
      const revision = await refresh(requiredRevision)
      if (active) verified.value = revision !== undefined && revision >= requiredRevision
    } catch {
      if (active) verified.value = false
    }
  }
  function acknowledge() {
    if (!verified.value || busy.value) return
    blocked.value = false
    error.value = null
    notice.value = ''
  }
  async function move(task: Task, columnId: string, beforeId: string | null) {
    const board = snapshot()
    if (!board || !writable() || busy.value || blocked.value || task.id === beforeId) return false
    if (
      !board.tasks.some((t) => t.id === task.id) ||
      !board.columns.some((c) => c.id === columnId) ||
      (beforeId !== null && !board.tasks.some((t) => t.id === beforeId && t.column_id === columnId))
    ) {
      error.value = new Error('Положение карточек изменилось. Выберите место заново.')
      return false
    }
    const order = orderedTasks(board.tasks, columnId)
    const at = order.findIndex((t) => t.id === task.id)
    if (at >= 0 && (order[at + 1]?.id ?? null) === beforeId) return false
    const body: TaskMove = {
      column_id: columnId,
      before_task_id: beforeId,
      expected_version: task.version,
    }
    busy.value = true
    error.value = null
    notice.value = ''
    verified.value = false
    pending.value = { task, columnId, beforeId }
    try {
      const result = await moveTask(task.id, body)
      if (!active) return false
      requiredRevision = Math.max(requiredRevision, result.board_revision)
      await verify()
      if (!active) return false
      notice.value = verified.value
        ? `${task.key}: задача перемещена`
        : 'Перенос сохранён. Обновите доску, чтобы увидеть подтверждённый порядок.'
      blocked.value = !verified.value
      return true
    } catch (e) {
      if (!active) return false
      error.value = e
      blocked.value =
        e instanceof ApiError && (e.status === 0 || e.status === 409 || e.status >= 500)
      notice.value = blocked.value
        ? 'Проверьте актуальный порядок. Перенос не будет повторён автоматически.'
        : ''
      pending.value = null
      await verify()
      return false
    } finally {
      if (active) {
        pending.value = null
        busy.value = false
      }
    }
  }
  return {
    busy,
    blocked,
    verified,
    pending,
    error,
    notice,
    move,
    verify,
    acknowledge,
    disabled: computed(() => busy.value || blocked.value || !writable()),
  }
}
