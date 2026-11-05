<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import PaginationBar from '../../components/PaginationBar.vue'
import type { Analytics } from '../../api/analytics'
import { completionChart, calendarLabel } from './chart-data'
const props = defineProps<{
  items: Analytics['completion_over_time']
  granularity: Analytics['granularity']
}>()
const chart = computed(() => completionChart(props.items))
const offset = ref(0)
watch(
  () => props.items,
  () => {
    offset.value = 0
  },
)
const rows = computed(() => props.items.slice(offset.value, offset.value + 20))
const showValues = ref(false)
</script>
<template>
  <section class="analytics-card">
    <h2>Первые завершения задач</h2>
    <p class="muted">
      Каждая задача учитывается один раз. Повторные завершения не добавляются; удалённые задачи
      остаются в истории.
      {{ granularity === 'month' ? 'Группировка по месяцам.' : 'Группировка по дням.' }}
    </p>
    <p v-if="!chart.total" role="status">За выбранный период первых завершений нет.</p>
    <svg
      v-if="items.length"
      class="completion-chart"
      viewBox="0 0 720 260"
      role="img"
      :aria-label="`Первые завершения: ${chart.total}. Максимум за ${granularity === 'month' ? 'месяц' : 'день'}: ${Math.max(0, ...items.map((i) => i.completed_count))}. Точные значения доступны в таблице ниже.`"
    >
      <line x1="48" y1="50" x2="672" y2="50" stroke="#dce5ed" />
      <line x1="48" y1="210" x2="672" y2="210" stroke="#a7b5c5" />
      <text x="38" y="55" text-anchor="end">{{ chart.maximum }}</text>
      <text x="38" y="215" text-anchor="end">0</text>
      <path :d="chart.path" fill="none" stroke="#16869e" stroke-width="3" />
      <circle
        v-if="chart.points.length === 1"
        :cx="chart.points[0]!.x"
        :cy="chart.points[0]!.y"
        r="5"
        fill="#16869e"
      />
      <template v-for="index in chart.ticks" :key="index">
        <text
          :x="chart.points[index]!.x"
          y="242"
          :text-anchor="index === 0 ? 'start' : index === items.length - 1 ? 'end' : 'middle'"
        >
          {{ calendarLabel(items[index]!.date, granularity) }}
        </text>
      </template>
    </svg>
    <Button
      :label="showValues ? 'Скрыть значения' : 'Показать точные значения'"
      text
      :aria-expanded="showValues"
      @click="showValues = !showValues"
    />
    <div v-if="showValues" class="analytics-table">
      <table>
        <caption>
          Завершения по
          {{
            granularity === 'month' ? 'месяцам' : 'дням'
          }}
        </caption>
        <thead>
          <tr>
            <th scope="col">Период</th>
            <th scope="col">Завершено впервые</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="point in rows" :key="point.date">
            <th scope="row">{{ calendarLabel(point.date, granularity) }}</th>
            <td>{{ point.completed_count }}</td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :offset="offset" :total="items.length" :limit="20" @change="offset = $event" />
    </div>
  </section>
</template>
<style scoped>
.completion-chart {
  display: block;
  width: 100%;
  height: auto;
  min-height: 180px;
}
.completion-chart text {
  font-family: inherit;
  font-size: 13px;
  fill: #526174;
}
.analytics-table {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
caption {
  text-align: left;
  padding: 10px 0;
  font-weight: 600;
}
th,
td {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #e5eaf0;
}
</style>
