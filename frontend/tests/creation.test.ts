import { afterEach, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { ApiError } from '../src/api/client'
import { useCreation } from '../src/features/projects/useCreation'
const scopes: ReturnType<typeof effectScope>[] = []
afterEach(() => {
  scopes.forEach((s) => s.stop())
  scopes.length = 0
  vi.restoreAllMocks()
})
function setup() {
  const scope = effectScope()
  scopes.push(scope)
  return scope.run(() => useCreation())!
}
it('prevents duplicate creation while pending and unlocks before navigation callback', async () => {
  const c = setup()
  let resolve!: (v: unknown) => void
  const action = vi.fn().mockReturnValue(
      new Promise((r) => {
        resolve = r
      }),
    ),
    accept = vi.fn(() => expect(c.busy.value).toBe(false))
  const first = c.run(action, accept)
  await c.run(action, accept)
  expect(action).toHaveBeenCalledTimes(1)
  resolve({ id: 'p' })
  await first
  expect(accept).toHaveBeenCalledWith({ id: 'p' })
})
it.each([0, 500])(
  'blocks retry after unknown result %s until explicit confirmation',
  async (status) => {
    const c = setup(),
      action = vi.fn().mockRejectedValue(new ApiError(status, 'ERROR', 'Error')),
      accept = vi.fn()
    await c.run(action, accept)
    await c.run(action, accept)
    expect(action).toHaveBeenCalledTimes(1)
    expect(accept).not.toHaveBeenCalled()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    c.allowRetry()
    expect(c.blocked.value).toBe(true)
    confirm.mockReturnValue(true)
    c.allowRetry()
    expect(c.blocked.value).toBe(false)
  },
)
it('does not close or clear the form on validation failure', async () => {
  const c = setup(),
    accept = vi.fn()
  await c.run(vi.fn().mockRejectedValue(new ApiError(422, 'VALIDATION_ERROR', 'Invalid')), accept)
  expect(accept).not.toHaveBeenCalled()
  expect(c.blocked.value).toBe(false)
  expect(c.error.value).toBeInstanceOf(ApiError)
})
it('ignores responses after leaving the page', async () => {
  const c = setup()
  let resolve!: (v: unknown) => void
  const accept = vi.fn()
  const pending = c.run(
    () =>
      new Promise((r) => {
        resolve = r
      }),
    accept,
  )
  scopes[0]!.stop()
  resolve({})
  await pending
  expect(accept).not.toHaveBeenCalled()
})
