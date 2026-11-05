<script setup lang="ts">
import { computed } from 'vue'
import type { Analytics } from '../../api/analytics'
const props = defineProps<{ items: Analytics['status_distribution'] }>()
const maximum = computed(() => Math.max(1, ...props.items.map((p) => p.count)))
const labels = { todo: 'К выполнению', in_progress: 'В работе', done: 'Завершено' }
</script>
<template>
  <section class="analytics-card">
    <h2>Задачи по колонкам</h2>
    <p class="muted">
      Текущее состояние всех досок проекта. Удалённые задачи не учитываются. Выбранный период не
      ограничивает этот график.
    </p>
    <p v-if="!items.length">В проекте пока нет колонок.</p>
    <p v-else-if="items.every((i) => i.count === 0)">В колонках пока нет задач.</p>
    <ul class="distribution-list">
      <li v-for="item in items" :key="item.column_id">
        <div class="distribution-label">
          <strong>{{ item.column_name }}</strong
          ><span>{{ item.board_name }} · {{ labels[item.category] }}</span>
        </div>
        <div class="distribution-track" aria-hidden="true">
          <span :class="item.category" :style="{ width: `${(item.count / maximum) * 100}%` }" />
        </div>
        <strong class="distribution-count"
          >{{ item.count }} <span class="sr-only">задач</span></strong
        >
      </li>
    </ul>
  </section>
</template>
<style scoped>
.distribution-list {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 18px;
}
.distribution-list li {
  display: grid;
  grid-template-columns: minmax(120px, 1fr) minmax(80px, 2fr) auto;
  gap: 14px;
  align-items: center;
}
.distribution-label {
  overflow-wrap: anywhere;
}
.distribution-label span {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.distribution-track {
  height: 14px;
  border-radius: 8px;
  background: #edf2f7;
  overflow: hidden;
}
.distribution-track span {
  display: block;
  height: 100%;
  border-radius: 8px;
}
.todo {
  background: #9b83df;
}
.in_progress {
  background: #249ab2;
}
.done {
  background: #4e9f77;
}
.distribution-count {
  min-width: 2ch;
  text-align: right;
}
@media (max-width: 600px) {
  .distribution-list li {
    grid-template-columns: minmax(100px, 1fr) minmax(60px, 1fr) auto;
    gap: 8px;
  }
}
</style>
