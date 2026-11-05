import { request } from './client'
import type { Project, ProjectCreate, Page, Board, Member, Snapshot } from './types'
export const listProjects = (offset = 0, signal?: AbortSignal) =>
  request<Page<Project>>(`/projects?limit=12&offset=${offset}`, { signal })
export const createProject = (body: ProjectCreate) =>
  request<Project>('/projects', { method: 'POST', body })
export const getProject = (id: string, signal?: AbortSignal) =>
  request<Project>(`/projects/${id}`, { signal })
export const listBoards = (id: string, offset = 0, signal?: AbortSignal) =>
  request<Page<Board>>(`/projects/${id}/boards?limit=12&offset=${offset}`, { signal })
export const listMembers = (id: string, offset = 0, signal?: AbortSignal) =>
  request<Page<Member>>(`/projects/${id}/members?limit=12&offset=${offset}`, { signal })
export const createBoard = (id: string, name: string) =>
  request<Board>(`/projects/${id}/boards`, { method: 'POST', body: { name } })
export const getBoard = (id: string, signal?: AbortSignal) =>
  request<Snapshot>(`/boards/${id}`, { signal })
