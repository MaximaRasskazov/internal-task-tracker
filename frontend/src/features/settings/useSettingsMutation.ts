import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { ApiError } from '../../api/client'
export function useSettingsMutation(allowed: () => boolean, reload: () => Promise<boolean>) {
  const busy = ref(false),
    blocked = ref(false),
    verified = ref(false),
    notice = ref('')
  const error = shallowRef<unknown>(null)
  let active = true
  onScopeDispose(() => {
    active = false
  })
  async function run(action: () => Promise<unknown>, success?: () => void) {
    if (busy.value || blocked.value || !allowed()) return false
    busy.value = true
    error.value = null
    notice.value = ''
    verified.value = false
    try {
      await action()
      if (!active) return false
      success?.()
      notice.value = 'Изменения сохранены'
      const fresh = await reload()
      if (active && !fresh) {
        blocked.value = true
        notice.value = 'Изменение сохранено. Обновите данные перед следующей операцией.'
      }
      return true
    } catch (e) {
      if (!active) return false
      error.value = e
      blocked.value =
        e instanceof ApiError &&
        (e.status === 0 || e.status >= 500 || e.code === 'VERSION_CONFLICT' || e.status === 403)
      return false
    } finally {
      if (active) busy.value = false
    }
  }
  async function verify() {
    if (busy.value) return
    busy.value = true
    verified.value = false
    try {
      const fresh = await reload()
      if (active) verified.value = fresh
    } catch {
      if (active) verified.value = false
    } finally {
      if (active) busy.value = false
    }
  }
  function acknowledge() {
    if (verified.value && !busy.value) {
      blocked.value = false
      error.value = null
    }
  }
  return {
    busy,
    blocked,
    verified,
    error,
    notice,
    run,
    verify,
    acknowledge,
    disabled: computed(() => busy.value || blocked.value || !allowed()),
  }
}
