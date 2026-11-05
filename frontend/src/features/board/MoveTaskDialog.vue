<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Button from 'primevue/button'
import type { Snapshot, Task } from '../../api/types'
import { orderedTasks } from './useTaskMove'
const props = defineProps<{
  board: Snapshot
  task: Task
  disabled: boolean
  busy: boolean
  visibleIds?: Set<string> | null
}>()
const emit = defineEmits<{ close: []; move: [task: Task, column: string, before: string | null] }>()
const column = ref(props.task.column_id)
const before = ref<string | null>(null)
const anchors = computed(() => [
  { name: 'В конец колонки', id: null },
  ...orderedTasks(props.board.tasks, column.value)
    .filter((t) => t.id !== props.task.id && (!props.visibleIds || props.visibleIds.has(t.id)))
    .map((t) => ({ id: t.id, name: `Перед ${t.key}: ${t.title}` })),
])
watch(column, () => {
  before.value = null
})
const valid = computed(
  () =>
    props.board.columns.some((c) => c.id === column.value) &&
    anchors.value.some((t) => t.id === before.value),
)
function submit() {
  if (!props.disabled && valid.value) emit('move', props.task, column.value, before.value)
}
</script>
<template>
  <Dialog
    :visible="true"
    modal
    :header="`Переместить ${task.key}`"
    :style="{ width: '30rem' }"
    :breakpoints="{ '650px': '96vw' }"
    :closable="!busy"
    :close-on-escape="!busy"
    @update:visible="!busy && emit('close')"
  >
    <form class="stack-form" @submit.prevent="submit">
      <p>{{ task.title }}</p>
      <label class="field"
        >Колонка<Select
          v-model="column"
          :options="board.columns"
          option-label="name"
          option-value="id"
          :disabled="busy"
      /></label>
      <label class="field"
        >Положение<Select
          v-model="before"
          :options="anchors"
          option-label="name"
          option-value="id"
          :disabled="busy"
      /></label>
      <p v-if="!valid" role="alert">
        Выбранное место изменилось. Выберите колонку и положение заново.
      </p>
      <p v-if="disabled && !busy" class="muted">
        Перенос временно недоступен. Закройте окно и проверьте состояние доски.
      </p>
      <div class="task-actions">
        <Button label="Отмена" text :disabled="busy" @click="emit('close')" /><Button
          type="submit"
          label="Переместить"
          :loading="busy"
          :disabled="disabled || !valid"
        />
      </div>
    </form>
  </Dialog>
</template>
