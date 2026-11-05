<script setup lang="ts">
import { computed, ref, shallowRef, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import Button from 'primevue/button'
import { getBoard } from '../../api/projects'
import { ApiError, errorMessage } from '../../api/client'
import type { Snapshot, Task } from '../../api/types'
import PageState from '../../components/PageState.vue'
import TaskPanel from '../task/TaskPanel.vue'
import TagManager from '../tags/TagManager.vue'
import { useSession } from '../../app/session'
import { useBoardRealtime } from './useBoardRealtime'
import KanbanBoard from './KanbanBoard.vue'
import MoveTaskDialog from './MoveTaskDialog.vue'
import { useTaskMove } from './useTaskMove'
import FormError from '../../components/FormError.vue'
import BoardFilters from './BoardFilters.vue'
import { readFilters, filterQuery, type Filters } from './filters'
import { useFilteredTasks } from './useFilteredTasks'
const route = useRoute()
const router = useRouter()
const data = shallowRef<Snapshot | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const tagManager = ref(false)
const tagsPanel = ref<InstanceType<typeof TagManager> | null>(null)
const session = useSession()
const canManageTags = computed(
  () => session.user?.role === 'admin' || session.user?.id === data.value?.project.owner_id,
)
function activityChanged(revision?: number) {
  if (revision !== undefined) minimumRevision = Math.max(minimumRevision, revision)
  void reload()
}
const creating = ref(false)
const initialColumn = ref('')
const panel = ref<InstanceType<typeof TaskPanel> | null>(null)
const taskId = computed(() => (typeof route.query.task === 'string' ? route.query.task : undefined))
let approvedClose = false
let generation = 0
let minimumRevision = 0
let controller: AbortController | undefined
const realtime = useBoardRealtime(
  String(route.params.boardId),
  async (revision) => {
    minimumRevision = Math.max(minimumRevision, revision)
    return reload()
  },
  (code) => {
    if (code === 4401) {
      session.clear()
      void router.replace({ path: '/login', query: { returnTo: route.fullPath } })
    }
    generation++
    controller?.abort()
    data.value = null
    loading.value = false
    error.value =
      code === 4401
        ? 'Сессия истекла. Войдите снова.'
        : code === 4404
          ? 'Доска удалена или недоступна.'
          : 'Доступ к доске закрыт.'
  },
)
const { writable, label: connectionLabel } = realtime
const filters = computed(() => readFilters(route.query))
const filtered = useFilteredTasks(
  String(route.params.boardId),
  () => filters.value,
  () => data.value?.revision,
  reload,
)
const {
  active: filtersActive,
  ready: filtersReady,
  ids: visibleIds,
  loading: filtersLoading,
  error: filtersError,
} = filtered
function applyFilters(value: Filters) {
  if (!moving.value) void router.push({ query: filterQuery(route.query, value) })
}
const movedTask = ref<string | null>(null)
watch([filtersReady, visibleIds], () => {
  if (movedTask.value && filtersReady.value) {
    if (visibleIds.value && !visibleIds.value.has(movedTask.value))
      notice.value = 'Задача перемещена и скрыта текущим фильтром'
    movedTask.value = null
  }
})
const selectedMove = shallowRef<Task | null>(null)
const mover = useTaskMove(
  () => data.value,
  () => writable.value && filtersReady.value,
  async (revision) => {
    if (revision !== undefined) minimumRevision = Math.max(minimumRevision, revision)
    return reload()
  },
)
const {
  busy: moving,
  blocked: moveBlocked,
  verified: moveVerified,
  pending: pendingMove,
  error: moveError,
  notice: moveNotice,
  disabled: moveDisabled,
} = mover
async function performMove(task: Task, column: string, before: string | null) {
  const done = await mover.move(task, column, before)
  if (done) {
    selectedMove.value = null
    if (filtersActive.value) {
      movedTask.value = task.id
      if (filtersReady.value) {
        if (visibleIds.value && !visibleIds.value.has(task.id))
          notice.value = 'Задача перемещена и скрыта текущим фильтром'
        movedTask.value = null
      }
    }
  }
}
async function reload() {
  if (realtime.state.value === 'closed') return
  controller?.abort()
  const current = ++generation
  controller = new AbortController()
  loading.value = true
  error.value = ''
  try {
    const board = await getBoard(String(route.params.boardId), controller.signal)
    if (current !== generation) return
    if (board.project.id !== route.params.projectId)
      throw new Error('Доска недоступна в этом проекте.')
    if (board.revision < Math.max(minimumRevision, data.value?.revision || 0))
      throw new Error('Получен устаревший снимок. Повторите обновление.')
    data.value = board
    return board.revision
  } catch (e) {
    if (current === generation && !controller.signal.aborted) {
      error.value = errorMessage(e)
      if (e instanceof ApiError && [401, 403, 404].includes(e.status))
        realtime.reject(e.status === 401 ? 4401 : e.status === 403 ? 4403 : 4404)
    }
  } finally {
    if (current === generation) loading.value = false
  }
}
function close() {
  creating.value = false
  if (taskId.value) {
    const query = { ...route.query }
    delete query.task
    approvedClose = true
    void router.push({ query })
  }
}
function create(column = '') {
  if (moving.value || !writable.value) return
  if (panel.value && !panel.value.canLeave()) return
  initialColumn.value = column
  creating.value = true
}
function open(id: string) {
  void router.push({ query: { ...route.query, task: id } })
}
function saved(revision: number, task?: Task) {
  minimumRevision = Math.max(minimumRevision, revision)
  notice.value = task ? 'Задача сохранена' : 'Задача удалена'
  creating.value = false
  if (task) void router.replace({ query: { ...route.query, task: task.id } })
  else close()
  void reload()
}
function canLeave() {
  return !moving.value && (tagsPanel.value?.canLeave() ?? true) && (panel.value?.canLeave() ?? true)
}
onBeforeRouteLeave((to) => (to.meta.public ? true : canLeave()))
onBeforeRouteUpdate((to, from) => {
  if (approvedClose) {
    approvedClose = false
    return true
  }
  return to.query.task !== from.query.task ? canLeave() : true
})
onMounted(reload)
onUnmounted(() => {
  generation++
  controller?.abort()
})
const columns = computed(() =>
  [...(data.value?.columns || [])]
    .sort((a, b) => a.position - b.position)
    .map((c) => ({
      ...c,
      tasks: (data.value?.tasks || [])
        .filter((t) => t.column_id === c.id)
        .sort((a, b) => a.position - b.position),
    })),
)
</script>
<template>
  <RouterLink class="back-link" :to="`/projects/${route.params.projectId}`"
    ><i class="pi pi-arrow-left" /> К проекту</RouterLink
  ><PageState v-if="!data" :loading="loading" :error="error" @retry="reload" /><template v-if="data"
    ><div class="page-heading">
      <div>
        <span class="eyebrow">{{ data.project.name }}</span>
        <h1>{{ data.board.name }}</h1>
        <p role="status" aria-live="polite">{{ connectionLabel }}</p>
      </div>
      <div class="task-actions">
        <RouterLink
          v-if="canManageTags"
          :to="`/projects/${data.project.id}/boards/${data.board.id}/settings`"
          class="back-link"
          >Настройки доски</RouterLink
        >
        <RouterLink :to="`/projects/${data.project.id}/analytics`" class="back-link"
          >Аналитика</RouterLink
        >
        <Button label="Теги" icon="pi pi-tags" outlined @click="tagManager = true" />
        <Button
          label="Обновить"
          icon="pi pi-refresh"
          outlined
          :loading="loading"
          @click="reload"
        /><Button
          label="Новая задача"
          icon="pi pi-plus"
          :disabled="!writable || moving || !columns.length"
          @click="create()"
        />
      </div>
    </div>
    <p v-if="notice" class="success-banner" role="status">{{ notice }}</p>
    <div v-if="error" class="error-banner" role="alert">
      {{ error }} <Button label="Повторить" text @click="reload" />
    </div>
    <p v-if="moving" role="status">Сохраняем новое положение…</p>
    <p v-if="moveNotice" class="info-banner" role="status">{{ moveNotice }}</p>
    <FormError :error="moveError" />
    <div v-if="moveBlocked" class="task-actions">
      <Button label="Проверить порядок" outlined :disabled="moving" @click="mover.verify" />
      <Button
        v-if="moveVerified"
        label="Проверил: разрешить новый перенос"
        text
        :disabled="moving"
        @click="mover.acknowledge"
      />
    </div>
    <BoardFilters :board="data" :value="filters" :disabled="moving" @apply="applyFilters" />
    <p v-if="filtersLoading" role="status">Ищем задачи…</p>
    <p v-if="filtersError" class="error-banner" role="alert">
      {{ filtersError }} <Button label="Повторить поиск" text @click="filtered.load" />
    </p>
    <p v-if="filtersActive && filtersReady" role="status">
      Найдено задач: {{ visibleIds?.size || 0 }} из {{ data.tasks.length }}. Пустые колонки остаются
      доступны для переноса.
    </p>
    <p v-if="filtersActive && filtersReady && !visibleIds?.size" class="info-banner">
      Задачи не найдены. Измените условия или сбросьте фильтры.
    </p>
    <KanbanBoard
      :visible-ids="visibleIds"
      :board="data"
      :disabled="moveDisabled"
      :pending="pendingMove"
      @open="open"
      @create="create"
      @choose-move="selectedMove = $event"
      @move="performMove" />
    <MoveTaskDialog
      v-if="selectedMove"
      :board="data"
      :task="selectedMove"
      :visible-ids="visibleIds"
      :disabled="moveDisabled"
      :busy="moving"
      @close="selectedMove = null"
      @move="performMove" />
    <PageState
      v-if="!columns.length"
      title="Пока нет колонок"
      description="Настройте колонки перед созданием задач." /></template
  ><TaskPanel
    v-if="data && (creating || taskId)"
    :key="creating ? `new-${initialColumn}` : taskId"
    ref="panel"
    :board="data"
    :read-only="!writable || moving"
    :task-id="creating ? undefined : taskId"
    :initial-column="initialColumn"
    @close="close"
    @saved="saved"
    @changed="activityChanged"
  />
  <TagManager
    v-if="data && tagManager"
    ref="tagsPanel"
    :project-id="data.project.id"
    :can-manage="canManageTags"
    :read-only="!writable || moving"
    @close="tagManager = false"
    @changed="reload"
  />
</template>
