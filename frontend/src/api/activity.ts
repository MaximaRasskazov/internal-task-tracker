import { request } from './client'
import type { Comment, Audit, Page, Tag, TagCreate, TagPatch } from './types'
export const listComments = (id: string, offset = 0, signal?: AbortSignal) =>
  request<Page<Comment>>(`/tasks/${id}/comments?limit=20&offset=${offset}`, { signal })
export const postComment = (id: string, text: string) =>
  request<{ data: Comment; board_id: string; board_revision: number }>(`/tasks/${id}/comments`, {
    method: 'POST',
    body: { text },
  })
export const listHistory = (id: string, offset = 0, signal?: AbortSignal) =>
  request<Page<Audit>>(`/tasks/${id}/history?limit=20&offset=${offset}`, { signal })
export const listTags = (project: string, offset = 0, signal?: AbortSignal) =>
  request<Page<Tag>>(`/projects/${project}/tags?limit=20&offset=${offset}`, { signal })
export const addTag = (project: string, body: TagCreate) =>
  request<Tag>(`/projects/${project}/tags`, { method: 'POST', body })
export const patchTag = (id: string, body: TagPatch) =>
  request<Tag>(`/tags/${id}`, { method: 'PATCH', body })
export const deleteTag = (id: string) => request<void>(`/tags/${id}`, { method: 'DELETE' })
