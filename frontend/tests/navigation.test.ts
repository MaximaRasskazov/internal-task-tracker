import { describe, expect, it } from 'vitest'
import { safeReturn } from '../src/app/navigation'
describe('return address', () => {
  it.each([
    'https://evil.test',
    '//evil.test',
    '/\\evil.test',
    '/login?returnTo=/login',
    '/register',
    undefined,
    ['/projects'],
  ])('rejects unsafe or recursive address %s', (value) => {
    expect(safeReturn(value)).toBe('/projects')
  })
  it('preserves local routes and their query', () => {
    expect(safeReturn('/projects/123?task=456')).toBe('/projects/123?task=456')
  })
})
