import type { Task, TaskPatch } from '../../api/types'
export type Draft = {
  title: string
  description: string
  priority: 'low' | 'medium' | 'high'
  assignee_id: string | null
  deadline: string | null
  story_points: number | null
  tag_ids: string[]
}
export const emptyDraft = (): Draft => ({
  title: '',
  description: '',
  priority: 'medium',
  assignee_id: null,
  deadline: null,
  story_points: null,
  tag_ids: [],
})
export function draftFrom(task: Task): Draft {
  return {
    title: task.title,
    description: task.description,
    priority: task.priority,
    assignee_id: task.assignee_id,
    deadline: task.deadline,
    story_points: task.story_points,
    tag_ids: [...task.tag_ids],
  }
}
export function changes(base: Draft, draft: Draft): Omit<TaskPatch, 'expected_version'> {
  const result: Record<string, unknown> = {}
  for (const key of Object.keys(base) as (keyof Draft)[]) {
    const before = key === 'tag_ids' ? [...base.tag_ids].sort() : base[key]
    const after = key === 'tag_ids' ? [...draft.tag_ids].sort() : draft[key]
    if (JSON.stringify(before) !== JSON.stringify(after)) result[key] = draft[key]
  }
  return result
}
export function rebaseDraft(base: Draft, draft: Draft, latest: Task): Draft {
  return { ...draftFrom(latest), ...changes(base, draft) } as Draft
}
export function canDelete(task: Task, userId: string, role: string, ownerId: string) {
  return role === 'admin' || userId === ownerId || userId === task.author_id
}
