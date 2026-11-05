<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { getBoard } from '../../api/projects'
import {
  patchBoard,
  deleteBoard,
  addColumn,
  patchColumn,
  deleteColumn,
  orderColumns,
  shiftedColumns,
  manages,
} from '../../api/settings'
import { useSession } from '../../app/session'
import { useResource } from '../useResource'
import { useSettingsMutation } from './useSettingsMutation'
import { useSettingsGuard } from './useSettingsGuard'
import MutationStatus from './MutationStatus.vue'
import PageState from '../../components/PageState.vue'
const route = useRoute(),
  router = useRouter(),
  session = useSession()
const id = String(route.params.boardId),
  projectId = String(route.params.projectId)
const resource = useResource(
  () => id,
  async (s) => {
    const result = await getBoard(id, s)
    if (result.project.id !== projectId) throw new Error('Доска недоступна в этом проекте.')
    return result
  },
)
const name = ref(''),
  baseName = ref(''),
  columnName = ref(''),
  columnBase = ref(''),
  editing = ref<string | null>(null)
const category = ref<'todo' | 'in_progress' | 'done'>('todo')
const dirty = computed(
  () =>
    name.value !== baseName.value ||
    columnName.value !== columnBase.value ||
    (!editing.value && category.value !== 'todo'),
)
watch(resource.data, (b) => {
  if (b && name.value === baseName.value) name.value = baseName.value = b.board.name
})
const allowed = computed(() => manages(session.user, resource.data.value?.project.owner_id))
async function reload() {
  await resource.reload()
  return !!resource.data.value
}
const mutation = useSettingsMutation(() => allowed.value, reload)
const { busy, disabled, error, notice, blocked, verified } = mutation
useSettingsGuard(
  () => dirty.value,
  () => busy.value,
)
const columns = computed(() =>
  [...(resource.data.value?.columns || [])].sort((a, b) => a.position - b.position),
)
function save() {
  if (name.value.trim())
    void mutation.run(
      () => patchBoard(id, name.value.trim()),
      () => {
        baseName.value = name.value = name.value.trim()
      },
    )
}
function resetColumn() {
  editing.value = null
  columnName.value = columnBase.value = ''
  category.value = 'todo'
}
function editColumn(column: (typeof columns.value)[number]) {
  if (
    columnName.value !== columnBase.value &&
    !window.confirm('Не сохранять текущие правки колонки?')
  )
    return
  editing.value = column.id
  columnName.value = columnBase.value = column.name
  category.value = column.category
}
function saveColumn() {
  if (!columnName.value.trim()) return
  void mutation.run(
    () =>
      editing.value
        ? patchColumn(editing.value, columnName.value.trim())
        : addColumn(id, { name: columnName.value.trim(), category: category.value }),
    resetColumn,
  )
}
function removeColumn(column: (typeof columns.value)[number]) {
  if (
    window.confirm(
      `Удалить колонку «${column.name}»? В ней не должно быть задач, включая удалённые.`,
    )
  )
    void mutation.run(
      () => deleteColumn(column.id),
      () => {
        if (editing.value === column.id) resetColumn()
      },
    )
}
function reorder(columnId: string, delta: number) {
  const board = resource.data.value
  if (!board) return
  const ids = shiftedColumns(board, columnId, delta)
  if (ids) void mutation.run(() => orderColumns(id, ids, board.revision))
}
async function removeBoard() {
  if (window.confirm('Удалить доску? Сначала должны быть удалены все её колонки.')) {
    const done = await mutation.run(
      () => deleteBoard(id),
      () => {
        name.value = baseName.value
        resetColumn()
      },
    )
    if (done) await router.replace(`/projects/${projectId}`)
  }
}
</script>
<template>
  <RouterLink class="back-link" :to="`/projects/${projectId}/boards/${id}`">К доске</RouterLink>
  <h1>Настройки доски</h1>
  <PageState
    v-if="!resource.data.value"
    :loading="resource.loading.value"
    :error="resource.error.value"
    @retry="reload"
  />
  <template v-else-if="allowed">
    <MutationStatus
      :error="error"
      :notice="notice"
      :blocked="blocked"
      :verified="verified"
      :busy="busy"
      @verify="mutation.verify"
      @acknowledge="mutation.acknowledge"
    />
    <section class="settings-section">
      <form class="settings-inline" @submit.prevent="save">
        <label class="field"
          >Название доски<InputText
            v-model="name"
            required
            maxlength="100"
            :disabled="busy" /></label
        ><Button type="submit" label="Сохранить" :disabled="disabled || !name.trim()" />
      </form>
    </section>
    <section class="settings-section">
      <h2>Колонки и порядок</h2>
      <p class="muted">
        Категория определяет завершённость задачи и задаётся только при создании колонки.
      </p>
      <ul class="settings-list">
        <li v-for="(column, index) in columns" :key="column.id">
          <div>
            <strong>{{ column.name }}</strong
            ><small>{{
              { todo: 'К выполнению', in_progress: 'В работе', done: 'Завершено' }[column.category]
            }}</small>
          </div>
          <div class="task-actions">
            <Button
              icon="pi pi-arrow-up"
              :aria-label="`Поднять ${column.name}`"
              text
              :disabled="disabled || index === 0"
              @click="reorder(column.id, -1)"
            /><Button
              icon="pi pi-arrow-down"
              :aria-label="`Опустить ${column.name}`"
              text
              :disabled="disabled || index === columns.length - 1"
              @click="reorder(column.id, 1)"
            /><Button
              label="Изменить"
              text
              :disabled="disabled"
              @click="editColumn(column)"
            /><Button
              label="Удалить"
              severity="danger"
              text
              :disabled="disabled"
              @click="removeColumn(column)"
            />
          </div>
        </li>
      </ul>
      <form class="stack-form" @submit.prevent="saveColumn">
        <h3>{{ editing ? 'Переименовать колонку' : 'Новая колонка' }}</h3>
        <label class="field"
          >Название<InputText
            v-model="columnName"
            required
            maxlength="100"
            :disabled="busy" /></label
        ><label class="field"
          >Категория<select v-model="category" :disabled="!!editing || busy">
            <option value="todo">К выполнению</option>
            <option value="in_progress">В работе</option>
            <option value="done">Завершено</option>
          </select></label
        >
        <div class="task-actions">
          <Button
            type="submit"
            :label="editing ? 'Сохранить колонку' : 'Создать колонку'"
            :disabled="disabled || !columnName.trim()"
          /><Button
            v-if="editing"
            label="Отмена правок"
            text
            :disabled="busy"
            @click="resetColumn"
          />
        </div>
      </form>
    </section>
    <section class="settings-section">
      <h2>Удаление доски</h2>
      <p>Для удаления на доске не должно быть колонок.</p>
      <Button
        label="Удалить доску"
        severity="danger"
        outlined
        :disabled="disabled"
        @click="removeBoard"
      />
    </section>
  </template>
  <p v-else role="alert">Настройки доступны руководителю проекта и администратору.</p>
</template>
