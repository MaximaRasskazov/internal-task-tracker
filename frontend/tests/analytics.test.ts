import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import PrimeVue from 'primevue/config'
import AnalyticsPage from '../src/features/analytics/AnalyticsPage.vue'
import StatusChart from '../src/features/analytics/StatusChart.vue'
import CompletionChart from '../src/features/analytics/CompletionChart.vue'
import { calendarLabel, completionChart, readPeriod } from '../src/features/analytics/chart-data'
import type { Analytics } from '../src/api/analytics'
const api = vi.hoisted(() => ({ getAnalytics: vi.fn() }))
vi.mock('../src/api/analytics', () => api)
const sample: Analytics = {
  project_id: 'p',
  timezone: 'Asia/Yekaterinburg',
  period: 'month',
  from: '2026-10-07',
  to: '2026-11-05',
  granularity: 'day',
  generated_at: '2026-11-05T00:00:00Z',
  status_distribution: [
    {
      board_id: 'b',
      board_name: 'First',
      column_id: 'c',
      column_name: 'Done',
      category: 'done',
      count: 2,
    },
    {
      board_id: 'b2',
      board_name: 'Second',
      column_id: 'c2',
      column_name: 'Done',
      category: 'done',
      count: 0,
    },
  ],
  completion_over_time: [
    { date: '2026-11-04', completed_count: 0 },
    { date: '2026-11-05', completed_count: 1 },
  ],
}
const wrappers: ReturnType<typeof mount>[] = []
beforeEach(() => {
  vi.resetAllMocks()
  api.getAnalytics.mockResolvedValue(sample)
})
afterEach(() => {
  wrappers.forEach((w) => w.unmount())
  wrappers.length = 0
})
async function setup(query = '') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/projects/:projectId/analytics', component: AnalyticsPage }],
  })
  await router.push('/projects/p/analytics' + query)
  await router.isReady()
  const w = mount(RouterView, { global: { plugins: [router, PrimeVue] } })
  wrappers.push(w)
  await flushPromises()
  return { w, router }
}
it('preserves calendar labels and accepts only supported periods', () => {
  expect(calendarLabel('2026-01-01')).toBe('01.01.2026')
  expect(calendarLabel('2026-01-01', 'month')).toBe('01.2026')
  expect(readPeriod('week')).toBe('week')
  expect(readPeriod('all')).toBe('all')
  expect(readPeriod('invalid')).toBe('month')
})
it('handles empty, zero and single-point series without invalid geometry', () => {
  expect(completionChart([]).path).toBe('')
  const zero = completionChart([{ date: '2026-11-05', completed_count: 0 }])
  expect(zero.points[0]).toMatchObject({ x: 360, y: 210 })
  expect(zero.maximum).toBe(1)
  const one = completionChart([{ date: '2026-11-05', completed_count: 5 }])
  expect(one.total).toBe(5)
  expect(one.points[0]?.y).toBe(50)
})
it('keeps same-named columns on different boards separate', () => {
  const w = mount(StatusChart, { props: { items: sample.status_distribution } })
  wrappers.push(w)
  expect(w.findAll('li')).toHaveLength(2)
  expect(w.text()).toContain('First')
  expect(w.text()).toContain('Second')
})
it('offers exact values including zero in an accessible table', async () => {
  const w = mount(CompletionChart, {
    props: { items: sample.completion_over_time, granularity: 'day' },
    global: { plugins: [PrimeVue] },
  })
  wrappers.push(w)
  await w.get('button').trigger('click')
  expect(w.get('table').text()).toContain('04.11.2026')
  expect(w.findAll('tbody td').map((c) => c.text())).toEqual(['0', '1'])
})
it('loads selected period from URL and separates current tasks from first completions', async () => {
  api.getAnalytics.mockResolvedValue({ ...sample, period: 'week' })
  const { w } = await setup('?period=week')
  expect(api.getAnalytics).toHaveBeenCalledWith('p', 'week', expect.any(AbortSignal))
  expect(w.findAll('.analytics-stats strong').map((c) => c.text())).toEqual(['2', '2', '1'])
  expect(w.text()).toContain('Asia/Yekaterinburg')
})
it('ignores an older period response after switching and supports history navigation', async () => {
  let resolve!: (v: Analytics) => void
  api.getAnalytics
    .mockReturnValueOnce(
      new Promise((r) => {
        resolve = r
      }),
    )
    .mockResolvedValue({ ...sample, period: 'all', granularity: 'month' })
  const { w, router } = await setup()
  await router.push('?period=all')
  await flushPromises()
  resolve(sample)
  await flushPromises()
  expect(w.text()).toContain('Группировка по месяцам.')
  expect(
    w
      .findAll('button')
      .find((b) => b.text() === 'Всё время')
      ?.attributes('aria-pressed'),
  ).toBe('true')
})
it('shows retryable failures without old statistics', async () => {
  api.getAnalytics.mockRejectedValue(new Error('Сервис недоступен'))
  const { w } = await setup()
  expect(w.text()).toContain('Сервис недоступен')
  expect(w.find('.analytics-stats').exists()).toBe(false)
})
