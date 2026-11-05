import { computed, onScopeDispose, shallowRef, ref } from 'vue'
import { listHistory } from '../../api/activity'
import { ApiError } from '../../api/client'
import type { Audit } from '../../api/types'
export function useHistory(id: string) {
  const items = shallowRef<Audit[]>([])
  const total = ref(0)
  const offset = ref(0)
  const loading = ref(false)
  const error = shallowRef<unknown>(null)
  let controller: AbortController | undefined
  let generation = 0
  async function load(reset = false) {
    if (loading.value && !reset) return
    controller?.abort()
    controller = new AbortController()
    const current = ++generation
    loading.value = true
    error.value = null
    const next = reset ? 0 : offset.value
    try {
      const page = await listHistory(id, next, controller.signal)
      if (current !== generation) return
      const existing = reset ? [] : items.value
      const ids = new Set(existing.map((i) => i.id))
      items.value = [...existing, ...page.items.filter((i) => !ids.has(i.id))]
      offset.value = next + page.items.length
      total.value = page.total
    } catch (e) {
      if (current === generation) {
        error.value = e
        if (e instanceof ApiError && [401, 403, 404].includes(e.status)) {
          items.value = []
          total.value = 0
        }
      }
    } finally {
      if (current === generation) loading.value = false
    }
  }
  onScopeDispose(() => {
    generation++
    controller?.abort()
  })
  return { items, total, loading, error, hasMore: computed(() => offset.value < total.value), load }
}
