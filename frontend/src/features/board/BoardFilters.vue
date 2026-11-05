<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import type { Snapshot } from '../../api/types'
import { emptyFilters, filterError, filterParams, type Filters } from './filters'
const props = defineProps<{ board: Snapshot; value: Filters; disabled: boolean }>()
const emit = defineEmits<{ apply: [filters: Filters] }>()
const draft = ref<Filters>(emptyFilters())
watch(
  () => props.value,
  (value) => {
    draft.value = {
      ...value,
      tag_ids: [...value.tag_ids],
      priority: [...value.priority],
      column_ids: [...value.column_ids],
    }
  },
  { immediate: true },
)
const error = computed(() => filterError(draft.value))
const active = computed(() => !!filterParams(props.value).toString())
const people = computed(() => {
  const members = new Map(props.board.members.map((m) => [m.user_id, m.name]))
  for (const task of props.board.tasks)
    if (task.assignee_id && !members.has(task.assignee_id))
      members.set(task.assignee_id, `${task.assignee?.name || 'Участник'} · вне проекта`)
  if (
    draft.value.assignee_id &&
    draft.value.assignee_id !== 'unassigned' &&
    !members.has(draft.value.assignee_id)
  )
    members.set(draft.value.assignee_id, 'Недоступный участник')
  return [
    { id: '', name: 'Все исполнители' },
    { id: 'unassigned', name: 'Не назначен' },
    ...Array.from(members, ([id, name]) => ({ id, name })),
  ]
})
const priorities = [
  { id: 'low', name: 'Низкий' },
  { id: 'medium', name: 'Средний' },
  { id: 'high', name: 'Высокий' },
]
function apply() {
  if (!props.disabled && !error.value) emit('apply', { ...draft.value, q: draft.value.q.trim() })
}
</script>
<template>
  <details class="board-filters" :open="active">
    <summary>Поиск и фильтры <span v-if="active" class="count-pill">Применены</span></summary>
    <form @submit.prevent="apply">
      <div class="filter-grid">
        <label class="field"
          >Название или ключ<InputText
            v-model="draft.q"
            maxlength="100"
            placeholder="Например, TEAM-12"
        /></label>
        <label class="field"
          >Исполнитель<Select
            v-model="draft.assignee_id"
            :options="people"
            option-label="name"
            option-value="id"
            filter
        /></label>
        <label class="field"
          >Теги — все выбранные<MultiSelect
            v-model="draft.tag_ids"
            :options="board.tags"
            option-label="name"
            option-value="id"
            filter
            placeholder="Все теги"
        /></label>
        <label class="field"
          >Приоритет<MultiSelect
            v-model="draft.priority"
            :options="priorities"
            option-label="name"
            option-value="id"
            placeholder="Любой"
        /></label>
        <label class="field"
          >Колонки<MultiSelect
            v-model="draft.column_ids"
            :options="board.columns"
            option-label="name"
            option-value="id"
            placeholder="Все колонки"
        /></label>
        <div class="date-range">
          <label class="field">Срок с<input v-model="draft.deadline_from" type="date" /></label
          ><label class="field"
            >Срок по<input
              v-model="draft.deadline_to"
              type="date"
              :min="draft.deadline_from || undefined"
          /></label>
        </div>
      </div>
      <p class="muted">
        Условия применяются вместе. При выборе срока задачи без срока не показываются.
      </p>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <div class="task-actions">
        <Button
          type="submit"
          label="Применить"
          icon="pi pi-filter"
          :disabled="disabled || !!error"
        /><Button
          label="Сбросить"
          text
          :disabled="disabled"
          @click="emit('apply', emptyFilters())"
        />
      </div>
    </form>
  </details>
</template>
<style scoped>
.board-filters {
  padding: 16px;
  margin-bottom: 18px;
  background: #fff;
  border: 1px solid #e5eaf0;
  border-radius: 14px;
}
summary {
  cursor: pointer;
  min-height: 44px;
  font-weight: 600;
}
.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.filter-grid > * {
  min-width: 0;
}
.date-range {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
input[type='date'] {
  min-width: 0;
  width: 100%;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
}
@media (max-width: 1000px) {
  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 600px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
