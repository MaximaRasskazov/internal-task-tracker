<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import type { Snapshot, Task } from '../../api/types'
import { tagColor } from '../task/history-format'
import { orderedTasks, previewTasks, type Placement } from './useTaskMove'
const props = defineProps<{
  board: Snapshot
  disabled: boolean
  pending: Placement | null
  visibleIds?: Set<string> | null
}>()
const emit = defineEmits<{
  open: [id: string]
  create: [column: string]
  chooseMove: [task: Task]
  move: [task: Task, column: string, before: string | null]
}>()
const dragged = ref<Task | null>(null)
const target = ref('')
const columns = computed(() =>
  [...props.board.columns]
    .sort((a, b) => a.position - b.position)
    .map((c) => ({
      ...c,
      tasks: orderedTasks(previewTasks(props.board.tasks, props.pending), c.id).filter(
        (t) => !props.visibleIds || props.visibleIds.has(t.id),
      ),
    })),
)
const priorities = { low: 'Низкий', medium: 'Средний', high: 'Высокий' }
function start(event: DragEvent, task: Task) {
  if (props.disabled || !event.dataTransfer) {
    event.preventDefault()
    return
  }
  dragged.value = task
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', task.id)
}
function over(event: DragEvent, column: string, before: string | null) {
  if (!dragged.value || props.disabled || before === dragged.value.id) return
  event.preventDefault()
  target.value = `${column}:${before || 'end'}`
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}
function cancel() {
  dragged.value = null
  target.value = ''
}
function drop(event: DragEvent, column: string, before: string | null) {
  event.preventDefault()
  if (dragged.value && !props.disabled && dragged.value.id !== before)
    emit('move', dragged.value, column, before)
  cancel()
}
</script>
<template>
  <p class="muted">Перетащите карточку к нужному месту или нажмите «Переместить».</p>
  <div class="kanban" @keydown.esc="cancel">
    <section v-for="column in columns" :key="column.id" :class="['kanban-column', column.category]">
      <h2>
        <span class="column-dot" />{{ column.name
        }}<span class="count-pill">{{ column.tasks.length }}</span>
      </h2>
      <template v-for="task in column.tasks" :key="task.id">
        <div
          :class="[
            'drop-slot',
            { 'drop-active': target === `${column.id}:${task.id}`, 'drop-visible': !!dragged },
          ]"
          aria-hidden="true"
          @dragover.stop="over($event, column.id, task.id)"
          @drop.stop="drop($event, column.id, task.id)"
        />
        <article
          class="movable-task"
          :class="{ 'task-pending': pending?.task.id === task.id }"
          :draggable="!disabled"
          @dragstart="start($event, task)"
          @dragend="cancel"
          @dragover.stop="over($event, column.id, task.id)"
          @drop.stop="drop($event, column.id, task.id)"
        >
          <button
            type="button"
            class="task-card task-card-button"
            :aria-label="`Открыть ${task.key}: ${task.title}`"
            @click="emit('open', task.id)"
          >
            <span class="task-key">{{ task.key }}</span
            ><span class="task-title">{{ task.title }}</span
            ><span class="task-meta"
              ><span :class="['priority', task.priority]">{{ priorities[task.priority] }}</span
              ><span v-if="task.story_points !== null">{{ task.story_points }} SP</span></span
            ><span class="task-tag-list"
              ><span v-for="id in task.tag_ids" :key="id" class="task-tag"
                ><span
                  class="tag-swatch"
                  :style="{
                    backgroundColor: tagColor(board.tags.find((t) => t.id === id)?.color || ''),
                  }"
                  aria-hidden="true"
                />{{ board.tags.find((t) => t.id === id)?.name || 'Тег' }}</span
              ></span
            ><span class="task-bottom"
              ><span>{{ task.assignee?.name || 'Не назначен' }}</span
              ><time v-if="task.deadline" :datetime="task.deadline">{{
                task.deadline.split('-').reverse().join('.')
              }}</time></span
            >
          </button>

          <Button
            label="Переместить"
            icon="pi pi-arrows-alt"
            text
            size="small"
            class="move-task-button"
            :aria-label="`Переместить ${task.key}`"
            :disabled="disabled"
            @click="emit('chooseMove', task)"
          />
        </article>
      </template>
      <div
        :class="['drop-end', { 'drop-active': target === `${column.id}:end` }]"
        @dragover="over($event, column.id, null)"
        @drop="drop($event, column.id, null)"
      >
        {{ !column.tasks.length ? 'Пока нет задач · перенесите сюда' : 'В конец колонки' }}
      </div>
      <Button
        label="Добавить задачу"
        icon="pi pi-plus"
        text
        severity="secondary"
        class="column-add"
        :disabled="disabled"
        @click="emit('create', column.id)"
      />
    </section>
  </div>
</template>
<style scoped>
.movable-task {
  background: white;
  border: 1px solid #e5eaf0;
  border-radius: 12px;
  overflow: hidden;
}
.movable-task[draggable='true'] {
  cursor: grab;
}
.movable-task .task-card {
  border: 0;
  margin-bottom: 0;
  border-radius: 0;
}
.move-task-button {
  min-height: 44px;
  width: 100%;
  justify-content: flex-start;
}
.task-pending {
  opacity: 0.65;
  outline: 2px dashed var(--primary-color, #0891b2);
}
.drop-slot {
  min-height: 12px;
  border-radius: 6px;
}
.drop-visible {
  min-height: 20px;
}
.drop-end {
  min-height: 44px;
  display: grid;
  place-items: center;
  padding: 8px;
  color: #64748b;
  font-size: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  margin: 10px 0;
}
.drop-active {
  background: #cffafe;
  box-shadow: inset 0 0 0 2px #0891b2;
}
</style>
