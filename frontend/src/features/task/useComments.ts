import { ref, shallowRef, onScopeDispose } from 'vue'
import type { Comment, Page } from '../../api/types'
import { listComments, postComment } from '../../api/activity'
import { ApiError } from '../../api/client'
export function useComments(id: string, saved: (revision: number) => void) {
  const draft = ref('')
  const busy = ref(false)
  const uncertain = ref(false)
  const verified = ref(false)
  const error = shallowRef<unknown>(null)
  const readError = shallowRef<unknown>(null)
  const page = shallowRef<Page<Comment> | null>(null)
  const offset = ref(0)
  const loading = ref(false)
  const sent = shallowRef<Comment | null>(null)
  const unavailable = ref(false)
  let controller: AbortController | undefined
  let generation = 0
  let active = true
  async function load(next = offset.value) {
    controller?.abort()
    controller = new AbortController()
    const current = ++generation
    loading.value = true
    readError.value = null
    try {
      const result = await listComments(id, next, controller.signal)
      if (current !== generation) return
      page.value = result
      offset.value = next
      verified.value = true
    } catch (e) {
      if (current === generation) {
        readError.value = e
        if (e instanceof ApiError && [401, 403, 404].includes(e.status)) {
          unavailable.value = true
          page.value = null
          sent.value = null
        }
      }
    } finally {
      if (current === generation) loading.value = false
    }
  }
  async function send() {
    if (
      busy.value ||
      uncertain.value ||
      unavailable.value ||
      !draft.value.trim() ||
      draft.value.trim().length > 5000
    )
      return
    busy.value = true
    error.value = null
    const text = draft.value.trim()
    try {
      const result = await postComment(id, text)
      if (!active) return
      draft.value = ''
      sent.value = result.data
      saved(result.board_revision)
      await load(offset.value)
    } catch (e) {
      if (active) {
        error.value = e
        if (e instanceof ApiError && (e.status === 0 || e.status >= 500)) {
          uncertain.value = true
          verified.value = false
          controller?.abort()
          generation++
          loading.value = false
        }
        if (e instanceof ApiError && [403, 404].includes(e.status)) unavailable.value = true
      }
    } finally {
      if (active) busy.value = false
    }
  }
  function allowRetry() {
    if (verified.value) {
      uncertain.value = false
      error.value = null
    }
  }
  onScopeDispose(() => {
    active = false
    generation++
    controller?.abort()
  })
  return {
    draft,
    busy,
    uncertain,
    verified,
    error,
    readError,
    page,
    offset,
    loading,
    sent,
    unavailable,
    load,
    send,
    allowRetry,
  }
}
