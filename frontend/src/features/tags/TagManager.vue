<script setup lang="ts">
import { computed, ref, shallowRef, onMounted, onUnmounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { addTag, patchTag, deleteTag, listTags } from '../../api/activity'
import { ApiError, fieldError } from '../../api/client'
import type { Tag } from '../../api/types'
import { useResource } from '../useResource'
import { tagColor } from '../task/history-format'
import FormError from '../../components/FormError.vue'
import PageState from '../../components/PageState.vue'
import PaginationBar from '../../components/PaginationBar.vue'
const props = defineProps<{ projectId: string; canManage: boolean; readOnly?: boolean }>()
const emit = defineEmits<{ close: []; changed: [] }>()
const offset = ref(0)
const name = ref('')
const color = ref('#64748B')
const editing = shallowRef<Tag | null>(null)
const busy = ref(false)
const error = shallowRef<unknown>(null)
const uncertain = ref(false)
const verified = ref(false)
const notice = ref('')
const {
  data,
  loading,
  error: loadError,
  reload,
} = useResource(
  () => `${props.projectId}:${offset.value}`,
  (signal) => listTags(props.projectId, offset.value, signal),
)
const dirty = computed(
  () =>
    name.value !== (editing.value?.name || '') ||
    color.value !== (editing.value?.color || '#64748B'),
)
async function verifyResult() {
  await reload()
  verified.value = !!data.value && !loadError.value
}
function discard() {
  return !busy.value && (!dirty.value || window.confirm('Не сохранять изменения тега?'))
}
function reset() {
  editing.value = null
  name.value = ''
  color.value = '#64748B'
  error.value = null
}
function start(tag?: Tag) {
  if (!discard() || uncertain.value) return
  reset()
  if (tag) {
    editing.value = tag
    name.value = tag.name
    color.value = tag.color
  }
}
function close() {
  if (discard()) emit('close')
}
function beforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value || busy.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}
async function mutate(action: () => Promise<unknown>) {
  if (props.readOnly || busy.value || uncertain.value) return
  busy.value = true
  error.value = null
  notice.value = ''
  try {
    await action()
    reset()
    notice.value = 'Теги обновлены'
    emit('changed')
    await reload()
  } catch (e) {
    error.value = e
    if (e instanceof ApiError && (e.status === 0 || e.status >= 500)) {
      uncertain.value = true
      verified.value = false
    }
  } finally {
    busy.value = false
  }
}
async function save() {
  if (
    !name.value.trim() ||
    !/^#[0-9a-f]{6}$/i.test(color.value) ||
    (editing.value && !props.canManage)
  )
    return
  const body = { name: name.value.trim(), color: color.value }
  await mutate(() =>
    editing.value ? patchTag(editing.value.id, body) : addTag(props.projectId, body),
  )
}
async function remove(tag: Tag) {
  if (!props.canManage || !discard()) return
  if (window.confirm(`Удалить тег «${tag.name}»?`)) await mutate(() => deleteTag(tag.id))
}
function allowRetry() {
  if (
    verified.value &&
    window.confirm(
      'Проверили список тегов? Повторная операция может быть лишней, если предыдущая уже сохранилась.',
    )
  ) {
    uncertain.value = false
    error.value = null
  }
}
defineExpose({ canLeave: discard })
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnload))
</script>
<template>
  <Dialog
    :visible="true"
    modal
    header="Теги проекта"
    :style="{ width: '38rem' }"
    :breakpoints="{ '650px': '96vw' }"
    :closable="!busy"
    :close-on-escape="!busy"
    @update:visible="close"
    ><p class="muted">
      Теги общие для всех досок проекта. Назначить тег задаче можно в её карточке.
    </p>
    <p v-if="notice" class="success-banner" role="status">{{ notice }}</p>
    <PageState v-if="loading || loadError" :loading="loading" :error="loadError" @retry="reload" />
    <ul v-else class="tag-manager-list">
      <li v-for="tag in data?.items" :key="tag.id">
        <span
          class="tag-swatch"
          :style="{ backgroundColor: tagColor(tag.color) }"
          aria-hidden="true"
        /><strong>{{ tag.name }}</strong
        ><template v-if="canManage"
          ><Button
            icon="pi pi-pencil"
            text
            :aria-label="`Изменить тег ${tag.name}`"
            :disabled="readOnly || busy || uncertain"
            @click="start(tag)" /><Button
            icon="pi pi-trash"
            text
            severity="danger"
            :aria-label="`Удалить тег ${tag.name}`"
            :disabled="readOnly || busy || uncertain"
            @click="remove(tag)"
        /></template>
      </li>
    </ul>
    <p v-if="!loading && !loadError && !data?.items.length" class="muted">
      Пока нет тегов. Создайте первый.
    </p>
    <PaginationBar
      v-if="data"
      :offset="offset"
      :total="data.total"
      :limit="20"
      @change="offset = $event" />
    <p v-if="!canManage" class="muted">
      Переименовывать и удалять теги может руководитель проекта или администратор.
    </p>
    <form class="stack-form tag-editor" @submit.prevent="save">
      <div class="section-heading">
        <h3>{{ editing ? 'Редактирование тега' : 'Новый тег' }}</h3>
        <Button
          v-if="editing"
          label="Отмена правок"
          text
          :disabled="readOnly || busy || uncertain"
          @click="start()"
        />
      </div>
      <label class="field"
        >Название<InputText
          v-model="name"
          required
          maxlength="40"
          :disabled="busy"
          :invalid="!!fieldError(error, 'name')"
        /><small class="field-error">{{ fieldError(error, 'name') }}</small></label
      >
      <div class="tag-color-row">
        <label class="field"
          >Цвет<input
            v-model="color"
            type="color"
            aria-label="Выбрать цвет тега"
            :disabled="busy" /></label
        ><label class="field"
          >HEX<InputText
            v-model="color"
            required
            pattern="#[0-9a-fA-F]{6}"
            maxlength="7"
            :disabled="busy"
          /><small class="field-error">{{ fieldError(error, 'color') }}</small></label
        >
      </div>
      <FormError :error="error" />
      <p v-if="error instanceof ApiError && error.code === 'TAG_IN_USE'" class="muted">
        Тег используется в задачах, в том числе удалённых. Его можно переименовать, если у вас есть
        права.
      </p>
      <div v-if="uncertain" class="info-banner">
        <p>Сервер мог сохранить изменение. Сначала обновите список и проверьте результат.</p>
        <Button label="Обновить список" :loading="loading" outlined @click="verifyResult" /><Button
          v-if="verified"
          label="Проверил результат"
          text
          @click="allowRetry"
        />
      </div>
      <Button
        type="submit"
        :label="editing ? 'Сохранить тег' : 'Создать тег'"
        :loading="busy"
        :disabled="
          readOnly ||
          uncertain ||
          !name.trim() ||
          (!!editing && !dirty) ||
          (!!editing && !canManage)
        "
      /></form
  ></Dialog>
</template>
