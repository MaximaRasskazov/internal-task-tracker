import { request } from './client'
import type { TaskCreate, TaskPatch, TaskRead, TaskMove } from './types'
export const readTask = (id: string, signal?: AbortSignal) =>
  request<TaskRead>(`/tasks/${id}`, { signal })
export const addTask = (boardId: string, body: TaskCreate) =>
  request<TaskRead>(`/boards/${boardId}/tasks`, { method: 'POST', body })
export const updateTask = (id: string, body: TaskPatch) =>
  request<TaskRead>(`/tasks/${id}`, { method: 'PATCH', body })
export const removeTask = (id: string, version: number) =>
  request<{ data: null; board_id: string; board_revision: number }>(
    `/tasks/${id}?expected_version=${version}`,
    { method: 'DELETE' },
  )

export const moveTask = (id: string, body: TaskMove) =>
  request<TaskRead>(`/tasks/${id}/move`, { method: 'POST', body })
