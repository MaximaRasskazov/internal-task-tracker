<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import { listProjects } from '../../api/projects'
import { useSession } from '../../app/session'
import { useResource } from '../useResource'
import PageState from '../../components/PageState.vue'
import PaginationBar from '../../components/PaginationBar.vue'
import CreateProjectDialog from './CreateProjectDialog.vue'
const session = useSession()
const router = useRouter()
const offset = ref(0)
const creating = ref(false)
const { data, loading, error, reload } = useResource(
  () => String(offset.value),
  (signal) => listProjects(offset.value, signal),
)
const tones = ['sky', 'violet', 'rose', 'green', 'amber', 'teal']
function tone(key: string) {
  return tones[Array.from(key).reduce((sum, c) => sum + c.charCodeAt(0), 0) % tones.length]
}
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">КОМАНДА НАЧИНАЕТСЯ С ОБЩЕЙ ЦЕЛИ</div>
      <h1>
        Проекты <span v-if="data" class="count-pill">{{ data.total }}</span>
      </h1>
      <p>Всё, над чем вы работаете вместе.</p>
    </div>
    <Button
      v-if="session.canCreateProject"
      label="Новый проект"
      icon="pi pi-plus"
      @click="creating = true"
    />
  </div>
  <section class="welcome-strip">
    <div>
      <span class="welcome-label">МЕСТО ДЛЯ ВАШИХ ИДЕЙ</span>
      <h2>От планов — к результатам</h2>
      <p>Выберите проект, чтобы увидеть доски и продолжить работу.</p>
    </div>
    <div class="welcome-shapes" aria-hidden="true"><span>✦</span><span>↗</span><span>✓</span></div>
  </section>
  <div class="section-heading">
    <h2>Ваши проекты</h2>
    <Button label="Обновить" text :loading="loading" @click="reload" />
    <span class="muted">{{
      session.user?.role === 'admin'
        ? 'Все проекты организации'
        : 'Проекты, к которым у вас есть доступ'
    }}</span>
  </div>
  <PageState v-if="loading || error" :loading="loading" :error="error" @retry="reload" />
  <PageState
    v-else-if="!data?.items.length"
    title="Здесь начнётся общая работа"
    :description="
      session.canCreateProject
        ? 'Создайте первый проект и соберите команду.'
        : 'Попросите руководителя добавить вас в проект по электронной почте.'
    "
    ><Button
      v-if="session.canCreateProject"
      label="Создать проект"
      icon="pi pi-plus"
      @click="creating = true"
  /></PageState>
  <template v-else
    ><div class="project-grid">
      <RouterLink
        v-for="project in data.items"
        :key="project.id"
        :to="`/projects/${project.id}`"
        :class="['project-card', tone(project.key)]"
        ><div class="project-card-top">
          <span class="project-symbol">{{ project.key.slice(0, 2) }}</span
          ><span class="project-key">{{ project.key }}</span
          ><i class="pi pi-arrow-up-right" aria-hidden="true" />
        </div>
        <h3>{{ project.name }}</h3>
        <p>{{ project.description || 'Общее пространство для задач и идей команды.' }}</p>
        <div class="project-card-footer">
          <span><i class="pi pi-objects-column" /> {{ project.board_count }} досок</span
          ><span><i class="pi pi-users" /> {{ project.member_count }} участников</span>
        </div></RouterLink
      >
    </div>
    <PaginationBar :offset="offset" :total="data.total" :limit="12" @change="offset = $event"
  /></template>
  <CreateProjectDialog
    v-if="session.canCreateProject"
    v-model="creating"
    @created="router.push(`/projects/${$event.id}`)"
  />
</template>
