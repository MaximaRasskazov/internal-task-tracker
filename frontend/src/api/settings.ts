import { request } from './client'
import type { components } from './generated/schema'
import type { Project, Member, User, Page, Board, Snapshot } from './types'
type Schema = components['schemas']
type Mutation<T> = { data: T; board_id: string; board_revision: number }
export const patchProject = (id: string, body: Schema['ProjectPatch']) =>
  request<Project>(`/projects/${id}`, { method: 'PATCH', body })
export const deleteProject = (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' })
export const addMember = (id: string, email: string) =>
  request<Member>(`/projects/${id}/members`, { method: 'POST', body: { email } })
export const removeMember = (id: string, user: string) =>
  request<void>(`/projects/${id}/members/${user}`, { method: 'DELETE' })
export const changeOwner = (id: string, user: string) =>
  request<Project>(`/projects/${id}/owner`, { method: 'PUT', body: { user_id: user } })
export const patchBoard = (id: string, name: string) =>
  request<Mutation<Board>>(`/boards/${id}`, { method: 'PATCH', body: { name } })
export const deleteBoard = (id: string) => request<void>(`/boards/${id}`, { method: 'DELETE' })
export const addColumn = (id: string, body: Schema['ColumnCreate']) =>
  request<Mutation<Schema['ColumnDto']>>(`/boards/${id}/columns`, { method: 'POST', body })
export const patchColumn = (id: string, name: string) =>
  request<Mutation<Schema['ColumnDto']>>(`/columns/${id}`, { method: 'PATCH', body: { name } })
export const deleteColumn = (id: string) => request<void>(`/columns/${id}`, { method: 'DELETE' })
export const orderColumns = (id: string, column_ids: string[], expected_revision: number) =>
  request<Mutation<Schema['ColumnDto'][]>>(`/boards/${id}/columns/order`, {
    method: 'PUT',
    body: { column_ids, expected_revision },
  })
export const listUsers = (q: string, offset: number, signal?: AbortSignal) =>
  request<Page<User>>(`/users?${new URLSearchParams({ q, offset: String(offset), limit: '20' })}`, {
    signal,
  })
export const changeRole = (id: string, role: User['role']) =>
  request<User>(`/users/${id}/role`, { method: 'PATCH', body: { role } })
export function manages(user: User | null, owner: string | undefined) {
  return !!user && (user.role === 'admin' || user.id === owner)
}
export function shiftedColumns(board: Snapshot, id: string, delta: number) {
  const ids = [...board.columns].sort((a, b) => a.position - b.position).map((c) => c.id)
  const from = ids.indexOf(id),
    to = from + delta
  if (from < 0 || to < 0 || to >= ids.length) return null
  const other = ids[to]!
  ids[to] = id
  ids[from] = other
  return ids
}
