import { computed, onMounted, onScopeDispose, ref } from 'vue'

type State = 'connecting' | 'syncing' | 'live' | 'offline' | 'closed'
/** Events invalidate snapshots; they never mutate task drafts or replay writes. */
export function useBoardRealtime(
  boardId: string,
  synchronize: (minimumRevision: number) => Promise<number | undefined>,
  denied: (code: number) => void,
) {
  const state = ref<State>('connecting')
  let socket: WebSocket | undefined
  let stopped = false
  let terminal = false
  let ready = false
  let epoch = 0
  let attempts = 0
  let maximum = 0
  let applied = -1
  let syncing = false
  let timer: ReturnType<typeof setTimeout> | undefined
  let watchdog: ReturnType<typeof setTimeout> | undefined
  let refreshTimer: ReturnType<typeof setTimeout> | undefined
  const seen = new Set<string>()
  function cancelTimers() {
    clearTimeout(timer)
    clearTimeout(watchdog)
    clearTimeout(refreshTimer)
  }
  function detach() {
    if (!socket) return
    socket.onmessage = null
    socket.onclose = null
    socket.onerror = null
    socket.close()
    socket = undefined
  }
  function reject(code: number) {
    terminal = true
    ready = false
    epoch++
    syncing = false
    cancelTimers()
    detach()
    state.value = 'closed'
    denied(code)
  }
  function retry() {
    if (stopped || terminal) return
    ready = false
    epoch++
    syncing = false
    cancelTimers()
    detach()
    state.value = 'offline'
    if (navigator.onLine) {
      const delay = Math.min(30000, 1000 * 2 ** Math.min(attempts++, 5))
      timer = setTimeout(connect, delay + Math.floor(Math.random() * 300))
    }
  }
  function watchConnection() {
    clearTimeout(watchdog)
    watchdog = setTimeout(retry, 35000)
  }
  async function refresh() {
    if (syncing || !ready || stopped || terminal) return
    clearTimeout(refreshTimer)
    syncing = true
    const current = epoch
    state.value = 'syncing'
    try {
      const revision = await synchronize(maximum)
      if (current !== epoch || stopped) return
      if (revision !== undefined) applied = Math.max(applied, revision)
      if (revision !== undefined && applied >= maximum) {
        state.value = 'live'
        attempts = 0
      } else refreshTimer = setTimeout(() => void refresh(), 1000)
    } catch {
      if (current === epoch && !stopped) refreshTimer = setTimeout(() => void refresh(), 2000)
    } finally {
      if (current === epoch) syncing = false
    }
  }
  function connect() {
    if (stopped || terminal) return
    cancelTimers()
    detach()
    epoch++
    syncing = false
    ready = false
    if (!navigator.onLine) {
      state.value = 'offline'
      return
    }
    state.value = 'connecting'
    try {
      const url = new URL(`/ws/v1/boards/${encodeURIComponent(boardId)}`, window.location.href)
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      const current = new WebSocket(url.toString())
      socket = current
      watchConnection()
      current.onmessage = (message) => {
        if (current !== socket || stopped) return
        let event: Record<string, unknown>
        try {
          event = JSON.parse(String(message.data))
        } catch {
          retry()
          return
        }
        if (
          !event ||
          event.board_id !== boardId ||
          typeof event.event_id !== 'string' ||
          typeof event.type !== 'string' ||
          !Number.isSafeInteger(event.board_revision) ||
          Number(event.board_revision) < 0
        ) {
          retry()
          return
        }
        watchConnection()
        if (seen.has(event.event_id)) return
        seen.add(event.event_id)
        if (seen.size > 1000) seen.delete(seen.values().next().value!)
        maximum = Math.max(maximum, Number(event.board_revision))
        if (event.type === 'board.deleted') {
          reject(4404)
          return
        }
        if (event.type === 'connection.ready') {
          ready = true
          void refresh()
        } else if (ready && maximum > applied) void refresh()
      }
      current.onclose = (event) => {
        if (current !== socket || stopped) return
        if ([4401, 4403, 4404].includes(event.code)) reject(event.code)
        else {
          retry()
          // Handshake errors hide the server close code in browsers. Probe HTTP for
          // session/access loss; this never enables writes before a new ready.
          void synchronize(maximum).catch(() => {})
        }
      }
      // Browsers also report handshake rejection as 1006; HTTP sync supplies access errors.
      current.onerror = () => {
        /* close or watchdog performs reconnect */
      }
    } catch {
      retry()
    }
  }
  function online() {
    connect()
  }
  function offline() {
    retry()
  }
  onMounted(() => {
    window.addEventListener('online', online)
    window.addEventListener('offline', offline)
    connect()
  })
  onScopeDispose(() => {
    stopped = true
    epoch++
    cancelTimers()
    detach()
    window.removeEventListener('online', online)
    window.removeEventListener('offline', offline)
  })
  const label = computed(
    () =>
      ({
        connecting: 'Подключаем обновления…',
        syncing: 'Сверяем данные…',
        live: 'Обновляется автоматически',
        offline: 'Нет соединения. Черновики сохранены, запись временно недоступна.',
        closed: 'Доска недоступна. Проверьте сессию и права доступа.',
      })[state.value],
  )
  return { state, label, writable: computed(() => state.value === 'live'), reject }
}
