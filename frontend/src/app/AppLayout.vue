<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import { useSession } from './session'
import { errorMessage } from '../api/client'
const session = useSession()
const router = useRouter()
const route = useRoute()
const menu = ref(false)
const busy = ref(false)
const error = ref('')
const roles = { admin: 'Администратор', pm: 'Руководитель', developer: 'Участник команды' }
async function logout() {
  busy.value = true
  error.value = ''
  try {
    await session.logout()
    await router.replace('/login')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function refresh() {
  try {
    await session.restore(true)
    if (!session.user) await router.replace({ path: '/login', query: { returnTo: route.fullPath } })
  } catch {
    /* Keep the last session during a temporary connection failure. */
  }
}
onMounted(() => window.addEventListener('focus', refresh))
onUnmounted(() => window.removeEventListener('focus', refresh))
</script>
<template>
  <a class="skip-link" href="#main">Перейти к содержимому</a>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink to="/projects" class="brand"
        ><span class="brand-icon"><i class="pi pi-th-large" /></span
        ><span>Трекер<span class="brand-sub">пространство команды</span></span></RouterLink
      >
      <div class="nav-caption">РАБОЧЕЕ ПРОСТРАНСТВО</div>
      <nav aria-label="Основная навигация">
        <RouterLink to="/projects" class="nav-link"
          ><i class="pi pi-folder" /> Проекты <i class="pi pi-angle-right"
        /></RouterLink>
        <RouterLink v-if="session.user?.role === 'admin'" to="/admin/users" class="nav-link"
          ><i class="pi pi-users" /> Пользователи</RouterLink
        >
      </nav>
      <div class="sidebar-note">
        <span class="note-orbit" aria-hidden="true">✦</span
        ><strong>Большие идеи.<br />Понятные шаги.</strong>
        <p>Вся работа команды<br />в одном пространстве.</p>
      </div>
      <div class="profile">
        <span class="avatar">{{ session.user?.name.slice(0, 1).toUpperCase() }}</span>
        <div>
          <strong>{{ session.user?.name }}</strong
          ><small>{{ session.user ? roles[session.user.role] : '' }}</small>
        </div>
        <Button
          icon="pi pi-sign-out"
          text
          severity="secondary"
          aria-label="Выйти"
          :loading="busy"
          @click="logout"
        />
      </div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <Button
          class="mobile-menu"
          icon="pi pi-bars"
          text
          aria-label="Открыть меню"
          @click="menu = true"
        /><span class="topbar-title">Работаем вместе <span class="small-dot" /></span
        ><span class="topbar-caption">Internal Task Tracker</span>
      </header>
      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
      <main id="main" tabindex="-1"><slot /></main>
    </div>
  </div>
  <Drawer v-model:visible="menu" header="Рабочее пространство"
    ><RouterLink class="nav-link" to="/projects" @click="menu = false"
      ><i class="pi pi-folder" /> Проекты</RouterLink
    >
    <RouterLink
      v-if="session.user?.role === 'admin'"
      to="/admin/users"
      class="nav-link"
      @click="menu = false"
      >Пользователи</RouterLink
    >
    <p>{{ session.user?.name }}</p>
    <Button label="Выйти" icon="pi pi-sign-out" :loading="busy" @click="logout"
  /></Drawer>
</template>
