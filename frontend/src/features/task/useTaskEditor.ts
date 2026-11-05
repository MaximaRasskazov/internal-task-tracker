import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import type { Task, TaskRead } from '../../api/types'
import { ApiError } from '../../api/client'
import { readTask, addTask, updateTask, removeTask } from '../../api/tasks'
import { emptyDraft, draftFrom, changes, rebaseDraft } from './draft'
export function useTaskEditor(
  boardId: string,
  taskId: string | undefined,
  initialColumn: string,
  saved: (revision: number, task?: Task) => void,
) {
  const task = shallowRef<Task | null>(null)
  const draft = ref(emptyDraft())
  const base = shallowRef(emptyDraft())
  const columnId = ref(initialColumn)
  const loading = ref(false)
  const busy = ref(false)
  const error = shallowRef<unknown>(null)
  const latest = shallowRef<Task | null>(null)
  const blocked = ref(false)
  const unavailable = ref(false)
  const dirty = computed(
    () =>
      Object.keys(changes(base.value, draft.value)).length > 0 ||
      (!task.value && columnId.value !== initialColumn),
  )
  const controller = new AbortController()
  let active = true
  onScopeDispose(() => {
    active = false
    controller.abort()
  })
  function accept(value: TaskRead) {
    if (value.board_id !== boardId) throw new Error('Задача не принадлежит этой доске.')
    task.value = value.data
    base.value = draftFrom(value.data)
    draft.value = draftFrom(value.data)
    columnId.value = value.data.column_id
  }
  async function load() {
    if (!taskId) return
    loading.value = true
    error.value = null
    try {
      const result = await readTask(taskId, controller.signal)
      if (active) accept(result)
    } catch (e) {
      if (active) {
        error.value = e
        unavailable.value = e instanceof ApiError && [403, 404].includes(e.status)
      }
    } finally {
      if (active) loading.value = false
    }
  }
  async function refreshConflict() {
    if (!taskId) return
    loading.value = true
    try {
      const result = await readTask(taskId, controller.signal)
      if (active) {
        if (result.board_id !== boardId) throw new Error('Задача недоступна.')
        latest.value = result.data
      }
    } catch (e) {
      if (active) {
        error.value = e
        unavailable.value = e instanceof ApiError && [403, 404].includes(e.status)
      }
    } finally {
      if (active) loading.value = false
    }
  }
  function resolveConflict(keep: boolean) {
    if (!latest.value) return
    const next = latest.value
    draft.value = keep ? rebaseDraft(base.value, draft.value, next) : draftFrom(next)
    base.value = draftFrom(next)
    task.value = next
    columnId.value = next.column_id
    latest.value = null
    blocked.value = false
    error.value = null
  }
  async function failed(e: unknown) {
    error.value = e
    if (e instanceof ApiError && [403, 404].includes(e.status)) unavailable.value = true
    if (e instanceof ApiError && (e.status === 409 || e.status === 0 || e.status >= 500)) {
      blocked.value = true
      await refreshConflict()
    }
  }
  async function save() {
    if (
      busy.value ||
      loading.value ||
      blocked.value ||
      unavailable.value ||
      (taskId && !task.value)
    )
      return
    const patch = task.value ? changes(base.value, draft.value) : null
    if (patch && !Object.keys(patch).length) return
    busy.value = true
    error.value = null
    try {
      const result = task.value
        ? await updateTask(task.value.id, { ...patch, expected_version: task.value.version })
        : await addTask(boardId, { ...draft.value, column_id: columnId.value })
      if (active) {
        accept(result)
        busy.value = false
        saved(result.board_revision, result.data)
      }
    } catch (e) {
      if (active) await failed(e)
    } finally {
      if (active) busy.value = false
    }
  }
  async function remove() {
    if (!task.value || busy.value || blocked.value || unavailable.value) return
    busy.value = true
    error.value = null
    try {
      const result = await removeTask(task.value.id, task.value.version)
      if (active) {
        base.value = { ...draft.value }
        busy.value = false
        saved(result.board_revision)
      }
    } catch (e) {
      if (active) await failed(e)
    } finally {
      if (active) busy.value = false
    }
  }
  function syncSnapshot(next: Task | undefined) {
    if (
      !task.value ||
      loading.value ||
      busy.value ||
      blocked.value ||
      !next ||
      next.version <= task.value.version
    )
      return
    if (dirty.value) {
      latest.value = next
      blocked.value = true
    } else {
      task.value = next
      base.value = draftFrom(next)
      draft.value = draftFrom(next)
      columnId.value = next.column_id
    }
  }
  void load()
  return {
    syncSnapshot,
    task,
    draft,
    columnId,
    dirty,
    loading,
    busy,
    error,
    latest,
    blocked,
    unavailable,
    load,
    save,
    remove,
    refreshConflict,
    resolveConflict,
  }
}
