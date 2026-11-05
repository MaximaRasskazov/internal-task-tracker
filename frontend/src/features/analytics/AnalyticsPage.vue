<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import { getAnalytics, type Period } from '../../api/analytics'
import { useResource } from '../useResource'
import PageState from '../../components/PageState.vue'
import StatusChart from './StatusChart.vue'
import CompletionChart from './CompletionChart.vue'
import { calendarLabel, readPeriod } from './chart-data'
const route = useRoute(),
  router = useRouter()
const id = String(route.params.projectId)
const period = computed(() => readPeriod(route.query.period))
const { data, loading, error, reload } = useResource(
  () => `${id}:${period.value}`,
  async (signal) => {
    const result = await getAnalytics(id, period.value, signal)
    if (result.project_id !== id || result.period !== period.value)
      throw new Error(
        'Ответ аналитики не соответствует выбранному проекту и периоду. Повторите загрузку.',
      )
    return result
  },
)
const periods: { value: Period; label: string }[] = [
  { value: 'week', label: '7 дней' },
  { value: 'month', label: '30 дней' },
  { value: 'all', label: 'Всё время' },
]
const currentTotal = computed(
  () => data.value?.status_distribution.reduce((sum, p) => sum + p.count, 0) || 0,
)
const doneTotal = computed(
  () =>
    data.value?.status_distribution
      .filter((p) => p.category === 'done')
      .reduce((sum, p) => sum + p.count, 0) || 0,
)
const completed = computed(
  () => data.value?.completion_over_time.reduce((sum, p) => sum + p.completed_count, 0) || 0,
)
function select(value: Period) {
  void router.push({ query: { ...route.query, period: value } })
}
function timestamp(value: string, timezone: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timezone,
  }).format(new Date(value))
}
</script>
<template>
  <RouterLink class="back-link" :to="`/projects/${id}`">К проекту</RouterLink>
  <div class="page-heading">
    <div>
      <span class="eyebrow">АНАЛИТИКА ПРОЕКТА</span>
      <h1>Как движется работа</h1>
      <p>Распределение задач и динамика первых завершений.</p>
    </div>
    <Button label="Обновить" icon="pi pi-refresh" outlined :loading="loading" @click="reload" />
  </div>
  <div class="analytics-periods" aria-label="Период аналитики">
    <Button
      v-for="item in periods"
      :key="item.value"
      :label="item.label"
      :outlined="period !== item.value"
      :aria-pressed="period === item.value"
      @click="select(item.value)"
    />
  </div>
  <PageState v-if="loading || error" :loading="loading" :error="error" @retry="reload" />
  <template v-else-if="data">
    <p class="muted">
      {{ calendarLabel(data.from) }} — {{ calendarLabel(data.to) }} · {{ data.timezone
      }}<br />Данные на {{ timestamp(data.generated_at, data.timezone) }}. Для новых изменений
      нажмите «Обновить».
    </p>
    <div class="analytics-stats">
      <article>
        <small>Задач сейчас</small><strong>{{ currentTotal }}</strong>
      </article>
      <article>
        <small>В завершённых колонках</small><strong>{{ doneTotal }}</strong>
      </article>
      <article>
        <small>Впервые завершено за период</small><strong>{{ completed }}</strong>
      </article>
    </div>
    <StatusChart :items="data.status_distribution" /><CompletionChart
      :items="data.completion_over_time"
      :granularity="data.granularity"
    />
  </template>
</template>
<style>
.analytics-periods {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 16px 0;
}
.analytics-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 22px 0;
}
.analytics-stats article,
.analytics-card {
  background: #fff;
  border: 1px solid #e5eaf0;
  border-radius: 16px;
  padding: 22px;
}
.analytics-stats article:nth-child(1) {
  background: #f4f0ff;
}
.analytics-stats article:nth-child(2) {
  background: #edf8f1;
}
.analytics-stats article:nth-child(3) {
  background: #edf8fc;
}
.analytics-stats strong {
  display: block;
  font-size: 32px;
  margin-top: 10px;
}
.analytics-card {
  margin-bottom: 20px;
}
.analytics-card h2 {
  margin-top: 0;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 600px) {
  .analytics-stats {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .analytics-card {
    padding: 16px;
  }
}
</style>
