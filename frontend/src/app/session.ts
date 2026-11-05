import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { request, configureSession, ApiError } from '../api/client'
import type { Session, Credentials, Registration, User } from '../api/types'
export const useSession = defineStore('session', () => {
  const session = shallowRef<Session | null>(null)
  const ready = shallowRef(false)
  const user = computed(() => session.value?.user ?? null)
  const canCreateProject = computed(() => user.value?.role === 'admin' || user.value?.role === 'pm')
  let pending: Promise<void> | null = null
  let generation = 0
  function accept(value: Session | null) {
    session.value = value
    configureSession(value?.csrf_token ?? null)
  }
  function clear() {
    generation++
    accept(null)
    ready.value = true
  }
  async function restore(force = false) {
    if (pending) return pending
    if (ready.value && !force) return
    const current = generation
    pending = (async () => {
      try {
        const value = await request<Session>('/auth/me', { public: true })
        if (current === generation) accept(value)
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          if (current === generation) accept(null)
        } else throw error
      }
      if (current === generation) ready.value = true
    })().finally(() => {
      pending = null
    })
    return pending
  }
  async function login(body: Credentials) {
    generation++
    accept(await request<Session>('/auth/login', { method: 'POST', body, public: true }))
    ready.value = true
  }
  async function register(body: Registration) {
    return request<User>('/auth/register', { method: 'POST', body, public: true })
  }
  async function logout() {
    await request<void>('/auth/logout', { method: 'POST' })
    clear()
  }
  return { user, ready, canCreateProject, restore, login, register, logout, clear }
})
