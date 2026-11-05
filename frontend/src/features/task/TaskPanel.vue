<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import InputNumber from 'primevue/inputnumber'
import type { Snapshot, Task } from '../../api/types'
import { fieldError } from '../../api/client'
import FormError from '../../components/FormError.vue'
import { useSession } from '../../app/session'
import { useTaskEditor } from './useTaskEditor'
import { canDelete } from './draft'
import TaskActivity from './TaskActivity.vue'
import TaskHistory from './TaskHistory.vue'
import TagManager from '../tags/TagManager.vue'
import { ApiError } from '../../api/client'
const props = defineProps<{
  board: Snapshot
  taskId?: string
  initialColumn?: string
  readOnly?: boolean
}>()
const emit = defineEmits<{
  close: []
  saved: [revision: number, task?: Task]
  changed: [revision?: number]
}>()
const commentDirty = ref(false)
const commentBusy = ref(false)
const tagManager = ref(false)
const tagsPanel = ref<InstanceType<typeof TagManager> | null>(null)
const canManageTags = computed(
  () => session.user?.role === 'admin' || session.user?.id === props.board.project.owner_id,
)
function activityState(dirty: boolean, busy: boolean) {
  commentDirty.value = dirty
  commentBusy.value = busy
}
const session = useSession()
const editor = useTaskEditor(
  props.board.board.id,
  props.taskId,
  props.initialColumn || props.board.columns[0]?.id || '',
  (revision, task) => emit('saved', revision, task),
)
const { task, draft, columnId, dirty, loading, busy, error, latest, blocked, unavailable } = editor
watch(
  [() => props.board.tasks.find((t) => t.id === props.taskId), busy, loading],
  ([next]) => editor.syncSnapshot(next),
  { immediate: true },
)
const priorities = [
  { label: 'Низкий', value: 'low' },
  { label: 'Средний', value: 'medium' },
  { label: 'Высокий', value: 'high' },
]
const members = computed(() => {
  const options = props.board.members
    .filter((m) => m.is_active)
    .map((m) => ({ label: m.name, value: m.user_id }))
  if (task.value?.assignee_id && !options.some((m) => m.value === task.value?.assignee_id))
    options.push({
      label: `${task.value.assignee?.name || 'Исполнитель'} · больше не участник`,
      value: task.value.assignee_id,
    })
  return [{ label: 'Не назначен', value: null }, ...options]
})
const removable = computed(
  () =>
    !!task.value &&
    !!session.user &&
    canDelete(task.value, session.user.id, session.user.role, props.board.project.owner_id),
)
function canLeave() {
  return (
    !busy.value &&
    !commentBusy.value &&
    (tagsPanel.value?.canLeave() ?? true) &&
    (!(dirty.value || commentDirty.value) ||
      window.confirm('Есть несохранённые изменения. Закрыть без сохранения?'))
  )
}
function close() {
  if (canLeave()) emit('close')
}
function beforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value || commentDirty.value || busy.value || commentBusy.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}
async function remove() {
  if (props.readOnly) return
  if (task.value && window.confirm(`Удалить задачу ${task.value.key} «${task.value.title}»?`))
    await editor.remove()
}
const date = (value: string) =>
  new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: props.board.project.timezone,
  }).format(new Date(value))
defineExpose({ canLeave })
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnload))
</script>
<template>
  <Drawer
    :visible="true"
    position="right"
    class="task-panel"
    :header="task ? task.key : taskId ? 'Задача' : 'Новая задача'"
    :dismissable="false"
    :close-on-escape="!busy && !commentBusy"
    :show-close-icon="!busy && !commentBusy"
    @update:visible="close"
    ><p v-if="loading" role="status">Загружаем актуальные данные…</p>
    <FormError :error="error" /><Button
      v-if="taskId && !task && !loading && !unavailable"
      label="Повторить загрузку"
      outlined
      @click="editor.load"
    />
    <TaskHistory
      v-if="taskId && unavailable && error instanceof ApiError && error.status === 404"
      :task-id="taskId"
      :timezone="board.project.timezone"
    />
    <div v-if="latest" class="conflict-panel" role="alert">
      <h3>Задача изменилась</h3>
      <p>
        Ваш текст сохранён в форме. Сверьте его с актуальными данными перед повторным сохранением.
      </p>
      <details>
        <summary>Данные на сервере · версия {{ latest.version }}</summary>
        <dl>
          <dt>Название</dt>
          <dd>{{ latest.title }}</dd>
          <dt>Описание</dt>
          <dd class="preserve-text">{{ latest.description || 'Не заполнено' }}</dd>
          <dt>Приоритет / исполнитель</dt>
          <dd>
            {{ priorities.find((p) => p.value === latest?.priority)?.label }} /
            {{ latest.assignee?.name || 'Не назначен' }}
          </dd>
          <dt>Срок / оценка</dt>
          <dd>{{ latest.deadline || 'Без срока' }} / {{ latest.story_points ?? 'Без оценки' }}</dd>
          <dt>Теги</dt>
          <dd>
            {{
              latest.tag_ids
                .map((id) => board.tags.find((t) => t.id === id)?.name || id)
                .join(', ') || 'Без тегов'
            }}
          </dd>
        </dl>
      </details>
      <div class="task-actions">
        <Button
          label="Сохранить мои правки в форме"
          outlined
          @click="editor.resolveConflict(true)"
        /><Button label="Взять данные сервера" text @click="editor.resolveConflict(false)" />
      </div>
      <small
        >Первый вариант сохранит изменённые вами поля. Остальные обновятся с сервера. Затем нажмите
        «Сохранить».</small
      >
    </div>
    <div v-else-if="blocked" class="info-banner">
      <p>Повторная запись остановлена: сначала проверьте, что уже сохранено.</p>
      <Button
        v-if="taskId && !unavailable"
        label="Перечитать задачу"
        :loading="loading"
        @click="editor.refreshConflict"
      />
      <p v-else>Закройте форму и обновите доску, прежде чем создавать задачу повторно.</p>
    </div>
    <p v-if="readOnly" class="info-banner" role="status">
      Восстанавливаем соединение. Ваши правки сохранены в форме; отправка временно недоступна.
    </p>
    <p
      v-else-if="task && board.tasks.find((t) => t.id === task?.id)?.version !== task.version"
      class="info-banner"
    >
      Задача изменилась в другой сессии или была удалена. Ваш черновик сохранён; при сохранении
      сервер проверит версию.
    </p>
    <form
      v-if="!taskId || task"
      class="stack-form task-form"
      @submit.prevent="!readOnly && editor.save()"
    >
      <fieldset :disabled="readOnly || busy || loading || unavailable">
        <label class="field"
          >Название<InputText
            v-model="draft.title"
            required
            maxlength="200"
            autofocus
            :invalid="!!fieldError(error, 'title')"
          /><small class="field-error">{{ fieldError(error, 'title') }}</small></label
        ><label class="field"
          >Описание<Textarea
            v-model="draft.description"
            rows="6"
            maxlength="20000"
            auto-resize
          /><small class="field-error">{{ fieldError(error, 'description') }}</small></label
        >
        <div class="field">
          <label for="task-column">Колонка</label
          ><Select
            v-if="!taskId"
            v-model="columnId"
            input-id="task-column"
            :options="board.columns"
            option-label="name"
            option-value="id"
            :invalid="!!fieldError(error, 'column_id')"
          />
          <p v-else class="read-value">
            {{ board.columns.find((c) => c.id === columnId)?.name || 'Колонка изменена' }}
          </p>
          <small v-if="taskId" class="muted"
            >Для изменения колонки используйте «Переместить» на карточке доски.</small
          >
        </div>
        <div class="task-fields-grid">
          <div class="field">
            <label for="task-priority">Приоритет</label
            ><Select
              v-model="draft.priority"
              input-id="task-priority"
              :options="priorities"
              option-label="label"
              option-value="value"
            />
          </div>
          <div class="field">
            <label for="task-assignee">Исполнитель</label
            ><Select
              v-model="draft.assignee_id"
              input-id="task-assignee"
              :options="members"
              option-label="label"
              option-value="value"
            /><small class="field-error">{{ fieldError(error, 'assignee_id') }}</small>
          </div>
          <label class="field"
            >Срок<input
              class="p-inputtext p-component"
              type="date"
              :value="draft.deadline || ''"
              min="0001-01-01"
              max="9999-12-31"
              @input="draft.deadline = ($event.target as HTMLInputElement).value || null"
            /><small class="field-error">{{ fieldError(error, 'deadline') }}</small></label
          >
          <div class="field">
            <label for="task-points">Оценка, SP</label
            ><InputNumber
              v-model="draft.story_points"
              input-id="task-points"
              :min="0"
              :max="100"
              :max-fraction-digits="0"
              :use-grouping="false"
              placeholder="Без оценки"
            /><small class="field-error">{{ fieldError(error, 'story_points') }}</small>
          </div>
        </div>
        <div class="field">
          <label for="task-tags">Теги проекта</label
          ><MultiSelect
            v-model="draft.tag_ids"
            input-id="task-tags"
            :options="board.tags"
            option-label="name"
            option-value="id"
            display="chip"
            :selection-limit="20"
            placeholder="Выберите теги"
            :disabled="!board.tags.length || busy || loading || unavailable"
          /><small v-if="!board.tags.length" class="muted">В проекте пока нет тегов.</small
          ><small class="field-error">{{ fieldError(error, 'tag_ids') }}</small>
          <Button
            label="Управление тегами"
            icon="pi pi-tags"
            text
            :disabled="busy || unavailable"
            @click="tagManager = true"
          />
        </div>
      </fieldset>
      <div v-if="task" class="task-audit-meta">
        <span>Автор: {{ task.author.name }}</span
        ><span>Создана: {{ date(task.created_at) }}</span
        ><span>Изменена: {{ date(task.updated_at) }}</span
        ><small>{{ board.project.timezone }}</small
        ><RouterLink :to="`/tasks/${task.id}`" target="_blank"
          >Постоянная ссылка <i class="pi pi-external-link"
        /></RouterLink>
      </div>
      <div class="task-save-bar">
        <span class="muted" role="status">{{
          dirty ? 'Есть несохранённые изменения' : task ? 'Все изменения сохранены' : ''
        }}</span>
        <div class="task-actions">
          <Button
            v-if="removable"
            label="Удалить"
            severity="danger"
            text
            :disabled="readOnly || busy || commentBusy || commentDirty || blocked || unavailable"
            @click="remove"
          /><Button
            label="Закрыть"
            severity="secondary"
            text
            :disabled="busy"
            @click="close"
          /><Button
            type="submit"
            :label="taskId ? 'Сохранить' : 'Создать задачу'"
            :loading="busy"
            :disabled="
              readOnly ||
              loading ||
              blocked ||
              unavailable ||
              !draft.title.trim() ||
              (!taskId && !columnId) ||
              (!!taskId && !dirty)
            "
          />
        </div>
      </div>
    </form>
    <TaskActivity
      v-if="task && !unavailable"
      :key="task.id"
      :task-id="task.id"
      :timezone="board.project.timezone"
      :revision="board.revision"
      :disabled="readOnly || busy"
      @saved="emit('changed', $event)"
      @state="activityState"
    />
    <TagManager
      v-if="tagManager"
      ref="tagsPanel"
      :project-id="board.project.id"
      :can-manage="canManageTags"
      :read-only="readOnly"
      @close="tagManager = false"
      @changed="emit('changed')"
    />
  </Drawer>
</template>
