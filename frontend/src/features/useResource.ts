import { shallowRef, ref, watch, onScopeDispose } from 'vue'
import { errorMessage } from '../api/client'
export function useResource<T>(key: () => string, fetcher: (signal: AbortSignal) => Promise<T>) {
  const data = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = ref('')
  let controller: AbortController | undefined
  let generation = 0
  async function reload() {
    controller?.abort()
    controller = new AbortController()
    const current = ++generation
    loading.value = true
    error.value = ''
    data.value = null
    try {
      const result = await fetcher(controller.signal)
      if (current === generation) data.value = result
    } catch (cause) {
      if (current === generation && !controller.signal.aborted) error.value = errorMessage(cause)
    } finally {
      if (current === generation) loading.value = false
    }
  }
  watch(key, reload, { immediate: true })
  onScopeDispose(() => {
    generation++
    controller?.abort()
  })
  return { data, loading, error, reload }
}
