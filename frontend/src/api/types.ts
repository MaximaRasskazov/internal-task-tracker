import type { components } from './generated/schema'
export type User = components['schemas']['UserDto']
export type Session = components['schemas']['SessionDto']
export type Project = components['schemas']['ProjectDto']
export type ProjectCreate = components['schemas']['ProjectCreate']
export type Board = components['schemas']['BoardDto']
export type Member = components['schemas']['MemberDto']
export type Snapshot = components['schemas']['BoardSnapshot']
export type Credentials = components['schemas']['Credentials']
export type Registration = components['schemas']['RegisterRequest']
export type Page<T> = { items: T[]; total: number; limit: number; offset: number }

export type Task = components['schemas']['TaskDto']
export type TaskCreate = components['schemas']['TaskCreate']
export type TaskPatch = components['schemas']['TaskPatch']
export type TaskRead = components['schemas']['TaskRead']

export type Comment = components['schemas']['CommentDto']
export type Audit = components['schemas']['AuditDto']
export type Tag = components['schemas']['TagDto']
export type TagCreate = components['schemas']['TagCreate']
export type TagPatch = components['schemas']['TagPatch']

export type TaskMove = components['schemas']['TaskMove']
