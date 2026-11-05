import { request } from './client'
import type { components } from './generated/schema'
export type Analytics = components['schemas']['AnalyticsDto']
export type Period = Analytics['period']
export const getAnalytics = (project: string, period: Period, signal?: AbortSignal) =>
  request<Analytics>(`/projects/${project}/analytics?period=${period}`, { signal })
