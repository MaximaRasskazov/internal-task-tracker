import { computed, onScopeDispose, ref, shallowRef, watch } from 'vue'
import { request, errorMessage } from '../../api/client'
import type { Task } from '../../api/types'
import { filterError, filterParams, type Filters } from './filters'
export function useFilteredTasks(
  boardId: string,
  filters: () => Filters,
  revision: () => number | undefined,
  refreshBoard: () => Promise<unknown>,
) {
  const items = shallowRef<Task[]>([])
  const loading = ref(false)
  const error = ref('')
  const accepted = ref('')
  const query = computed(() => filterParams(filters()).toString())
  const active = computed(() => !!query.value)
  const key = computed(() => `${revision()}:${query.value}`)
  let generation = 0
  let controller: AbortController | undefined
  async function load() {
    controller?.abort()
    controller = new AbortController()
    const current = ++generation
    error.value = ''
    accepted.value = ''
    items.value = []
    loading.value = false
    if (!active.value || revision() === undefined) return
    error.value = filterError(filters())
    if (error.value) return
    const expected = revision()!
    const requestedKey = key.value
    loading.value = true
    try {
      const result = await request<{ items: Task[]; total: number; board_revision: number }>(
        `/boards/${boardId}/tasks?${query.value}`,
        { signal: controller.signal },
      )
      if (current !== generation) return
      if (result.board_revision !== expected) {
        error.value = 'Доска изменилась. Обновляем данные; при необходимости повторите поиск.'
        await refreshBoard()
        return
      }
      items.value = result.items
      accepted.value = requestedKey
    } catch (e) {
      if (current === generation) error.value = errorMessage(e)
    } finally {
      if (current === generation) loading.value = false
    }
  }
  watch(key, load, { immediate: true })
  onScopeDispose(() => {
    generation++
    controller?.abort()
  })
  const ready = computed(() => !active.value || accepted.value === key.value)
  const ids = computed(() => (active.value ? new Set(items.value.map((t) => t.id)) : null))
  return { active, ready, ids, items, loading, error, load }
}
