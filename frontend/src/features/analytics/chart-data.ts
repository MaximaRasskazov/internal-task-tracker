import type { Analytics, Period } from '../../api/analytics'
export function readPeriod(value: unknown): Period {
  return value === 'week' || value === 'all' ? value : 'month'
}
export function calendarLabel(date: string, granularity: 'day' | 'month' = 'day') {
  const [year, month, day] = date.split('-')
  return granularity === 'month' ? `${month}.${year}` : `${day}.${month}.${year}`
}
export function completionChart(items: Analytics['completion_over_time']) {
  const maximum = Math.max(1, ...items.map((p) => p.completed_count))
  const points = items.map((p, i) => ({
    ...p,
    x: items.length === 1 ? 360 : 48 + (i * 624) / Math.max(1, items.length - 1),
    y: 210 - (p.completed_count / maximum) * 160,
  }))
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ')
  const ticks = [...new Set([0, Math.floor((items.length - 1) / 2), items.length - 1])].filter(
    (i) => i >= 0,
  )
  return {
    maximum,
    points,
    path,
    ticks,
    total: items.reduce((sum, p) => sum + p.completed_count, 0),
  }
}
