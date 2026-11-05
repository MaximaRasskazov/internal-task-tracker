import type { LocationQuery, LocationQueryRaw } from 'vue-router'
export type Filters = {
  q: string
  assignee_id: string
  tag_ids: string[]
  priority: string[]
  column_ids: string[]
  deadline_from: string
  deadline_to: string
}
export const filterKeys = [
  'q',
  'assignee_id',
  'tag_ids',
  'priority',
  'column_ids',
  'deadline_from',
  'deadline_to',
] as const
export const emptyFilters = (): Filters => ({
  q: '',
  assignee_id: '',
  tag_ids: [],
  priority: [],
  column_ids: [],
  deadline_from: '',
  deadline_to: '',
})
export function readFilters(query: LocationQuery): Filters {
  const first = (key: string) => {
    const v = query[key]
    return (Array.isArray(v) ? v[0] : v) || ''
  }
  const many = (key: string) => {
    const v = query[key]
    return [
      ...new Set(
        (Array.isArray(v) ? v : [v]).filter((s): s is string => typeof s === 'string' && !!s),
      ),
    ]
  }
  return {
    q: first('q'),
    assignee_id: first('assignee_id'),
    tag_ids: many('tag_ids'),
    priority: many('priority'),
    column_ids: many('column_ids'),
    deadline_from: first('deadline_from'),
    deadline_to: first('deadline_to'),
  }
}
export function filterParams(filters: Filters) {
  const params = new URLSearchParams()
  for (const key of filterKeys) {
    const value = filters[key]
    for (const item of Array.isArray(value) ? value : [value]) if (item) params.append(key, item)
  }
  return params
}
export function filterQuery(query: LocationQuery, filters: Filters): LocationQueryRaw {
  const next: LocationQueryRaw = { ...query }
  for (const key of filterKeys) {
    delete next[key]
    const value = filters[key]
    if (Array.isArray(value) ? value.length : value) next[key] = value
  }
  return next
}
function dateValid(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = new Date(value + 'T00:00:00Z')
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}
export function filterError(filters: Filters): string {
  if (filters.q.length > 100) return 'Поиск: не больше 100 символов.'
  if (filters.priority.some((p) => !['low', 'medium', 'high'].includes(p)))
    return 'Неизвестный приоритет в ссылке. Сбросьте или исправьте фильтр.'
  if ([filters.deadline_from, filters.deadline_to].some((v) => v && !dateValid(v)))
    return 'Укажите корректные даты.'
  if (filters.deadline_from && filters.deadline_to && filters.deadline_from > filters.deadline_to)
    return 'Дата «по» должна быть не раньше даты «с».'
  return ''
}
