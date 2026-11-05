import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useBoardRealtime } from '../src/features/board/useBoardRealtime'
class Socket {
  static all: Socket[] = []
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  onerror: (() => void) | null = null
  close = vi.fn()
  constructor(public url: string) {
    Socket.all.push(this)
  }
  event(type: string, revision: number, id = `${type}-${revision}`) {
    this.onmessage?.({
      data: JSON.stringify({ type, board_revision: revision, board_id: 'b', event_id: id }),
    })
  }
}
const wrappers: ReturnType<typeof mount>[] = []
beforeEach(() => {
  vi.useFakeTimers()
  Socket.all = []
  vi.stubGlobal('WebSocket', Socket)
  vi.spyOn(Math, 'random').mockReturnValue(0)
})
afterEach(() => {
  wrappers.forEach((w) => w.unmount())
  wrappers.length = 0
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
function setup(
  sync = vi
    .fn<(revision: number) => Promise<number | undefined>>()
    .mockImplementation(async (r) => r),
) {
  const denied = vi.fn()
  let state!: ReturnType<typeof useBoardRealtime>
  const wrapper = mount(
    defineComponent({
      setup() {
        state = useBoardRealtime('b', sync, denied)
        return () => null
      },
    }),
  )
  wrappers.push(wrapper)
  return { state, sync, denied, wrapper, socket: Socket.all[0]! }
}
it('waits for ready and snapshot before allowing writes; uses cookie-only URL', async () => {
  const { state, socket, sync } = setup()
  expect(socket.url).toMatch(/^ws:\/\/.*\/ws\/v1\/boards\/b$/)
  expect(state.writable.value).toBe(false)
  expect(sync).not.toHaveBeenCalled()
  socket.event('connection.ready', 4)
  await flushPromises()
  expect(sync).toHaveBeenCalledWith(4)
  expect(state.writable.value).toBe(true)
})
it('deduplicates events and ignores lower revisions', async () => {
  const { socket, sync } = setup()
  socket.event('connection.ready', 4)
  await flushPromises()
  socket.event('task.updated', 5, 'same')
  await flushPromises()
  socket.event('task.updated', 5, 'same')
  socket.event('heartbeat', 3)
  await flushPromises()
  expect(sync).toHaveBeenCalledTimes(2)
})
it('catches up when an event arrives during the snapshot request', async () => {
  let resolve!: (n: number) => void
  const sync = vi
    .fn<(r: number) => Promise<number | undefined>>()
    .mockReturnValueOnce(
      new Promise((r) => {
        resolve = r
      }),
    )
    .mockResolvedValue(6)
  const { socket, state } = setup(sync)
  socket.event('connection.ready', 4)
  socket.event('task.updated', 6)
  resolve(4)
  await flushPromises()
  expect(state.writable.value).toBe(false)
  await vi.advanceTimersByTimeAsync(1000)
  await flushPromises()
  expect(sync).toHaveBeenLastCalledWith(6)
  expect(state.writable.value).toBe(true)
})
it('retries failed snapshot reads without reconnecting or replaying writes', async () => {
  const sync = vi
    .fn<(r: number) => Promise<number | undefined>>()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue(2)
  const { socket, state } = setup(sync)
  socket.event('connection.ready', 2)
  await flushPromises()
  expect(state.writable.value).toBe(false)
  await vi.advanceTimersByTimeAsync(2000)
  await flushPromises()
  expect(state.writable.value).toBe(true)
  expect(Socket.all).toHaveLength(1)
})
it('detects silence after 35 seconds and requires ready plus a new snapshot', async () => {
  const { socket, state, sync } = setup()
  socket.event('connection.ready', 2)
  await flushPromises()
  await vi.advanceTimersByTimeAsync(35000)
  expect(state.state.value).toBe('offline')
  expect(socket.close).toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(1000)
  expect(Socket.all).toHaveLength(2)
  expect(state.writable.value).toBe(false)
  Socket.all[1]!.event('connection.ready', 2, 'new-ready')
  await flushPromises()
  expect(sync).toHaveBeenCalledTimes(2)
  expect(state.writable.value).toBe(true)
})
it.each([4401, 4403, 4404])('stops reconnect after terminal close %s', async (code) => {
  const { socket, state, denied } = setup()
  socket.onclose?.({ code })
  await vi.advanceTimersByTimeAsync(120000)
  expect(denied).toHaveBeenCalledWith(code)
  expect(state.state.value).toBe('closed')
  expect(Socket.all).toHaveLength(1)
})
it('closes and clears timers on unmount, ignoring late HTTP completion', async () => {
  let resolve!: (n: number) => void
  const sync = vi.fn<(r: number) => Promise<number | undefined>>().mockReturnValue(
    new Promise((r) => {
      resolve = r
    }),
  )
  const { socket, wrapper, state } = setup(sync)
  socket.event('connection.ready', 1)
  wrapper.unmount()
  resolve(1)
  await flushPromises()
  await vi.advanceTimersByTimeAsync(120000)
  expect(state.writable.value).toBe(false)
  expect(Socket.all).toHaveLength(1)
  expect(socket.close).toHaveBeenCalled()
  expect(vi.getTimerCount()).toBe(0)
})
