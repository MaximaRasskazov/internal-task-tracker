import { ref, shallowRef, onScopeDispose } from 'vue'
import { ApiError } from '../../api/client'
export function useCreation() {
  const busy = ref(false),
    blocked = ref(false),
    error = shallowRef<unknown>(null)
  let active = true
  onScopeDispose(() => {
    active = false
  })
  async function run<T>(action: () => Promise<T>, accept: (value: T) => void) {
    if (busy.value || blocked.value) return
    busy.value = true
    error.value = null
    try {
      const value = await action()
      if (active) {
        busy.value = false
        accept(value)
      }
    } catch (e) {
      if (active) {
        error.value = e
        blocked.value = e instanceof ApiError && (e.status === 0 || e.status >= 500)
      }
    } finally {
      if (active) busy.value = false
    }
  }
  function allowRetry() {
    if (
      !busy.value &&
      window.confirm(
        'Вы проверили список и убедились, что объект не создан? Повтор может создать дубликат, если предыдущая операция сохранилась.',
      )
    ) {
      blocked.value = false
      error.value = null
    }
  }
  return { busy, blocked, error, run, allowRetry }
}
