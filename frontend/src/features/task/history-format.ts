export const eventLabels: Record<string, string> = {
  'task.created': 'Создана задача',
  'task.updated': 'Изменены поля',
  'task.moved': 'Задача перемещена',
  'task.completed': 'Задача завершена',
  'task.reopened': 'Задача возвращена в работу',
  'task.deleted': 'Задача удалена',
  'comment.created': 'Добавлен комментарий',
}
export const fieldLabels: Record<string, string> = {
  title: 'Название',
  description: 'Описание',
  column_id: 'Колонка',
  priority: 'Приоритет',
  assignee_id: 'Исполнитель',
  deadline: 'Срок',
  story_points: 'Оценка, SP',
  tag_ids: 'Теги',
  position: 'Позиция',
  deleted_at: 'Удалена',
  is_completed: 'Завершена',
  comment_id: 'Комментарий',
}
export function historyValue(value: unknown, field: string): string {
  if (value === null || value === undefined || value === '') return 'Не заполнено'
  if (Array.isArray(value))
    return value.length ? value.map((v) => historyValue(v, field)).join(', ') : 'Нет'
  if (typeof value === 'object') {
    const object = value as Record<string, unknown>
    return typeof object.name === 'string' ? object.name : JSON.stringify(value)
  }
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (field === 'priority')
    return (
      ({ low: 'Низкий', medium: 'Средний', high: 'Высокий' } as Record<string, string>)[
        String(value)
      ] || String(value)
    )
  if (field === 'deadline' && typeof value === 'string') return value.split('-').reverse().join('.')
  return String(value)
}
export function formatActivityDate(value: string, timezone = 'UTC') {
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timezone,
  }).format(new Date(value))
}
export function tagColor(value: string) {
  return /^#[0-9a-f]{6}$/i.test(value) ? value : '#64748B'
}
