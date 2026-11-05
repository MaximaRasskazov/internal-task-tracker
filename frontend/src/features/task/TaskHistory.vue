<script setup lang="ts">
import { onMounted, watch } from 'vue'
import Button from 'primevue/button'
import FormError from '../../components/FormError.vue'
import { useHistory } from './useHistory'
import { eventLabels, fieldLabels, historyValue, formatActivityDate } from './history-format'
const props = withDefaults(
  defineProps<{ taskId: string; timezone?: string; revision?: number }>(),
  { timezone: 'UTC', revision: 0 },
)
const history = useHistory(props.taskId)
const { items, total, loading, error, hasMore } = history
onMounted(() => history.load(true))
watch(
  () => props.revision,
  () => history.load(true),
)
</script>
<template>
  <section class="activity-section" aria-label="История изменений">
    <div class="section-heading">
      <h3>
        История изменений <span class="count-pill">{{ total }}</span>
      </h3>
      <Button
        label="Обновить"
        icon="pi pi-refresh"
        text
        :loading="loading"
        @click="history.load(true)"
      />
    </div>
    <small class="muted">От ранних событий к поздним · {{ timezone }}</small
    ><FormError :error="error" /><Button
      v-if="error"
      label="Повторить загрузку"
      outlined
      @click="history.load(items.length === 0)"
    />
    <p v-if="loading" role="status">Загружаем историю…</p>
    <p v-else-if="!items.length && !error" class="muted">Изменений пока нет.</p>
    <ol class="history-list">
      <li v-for="entry in items" :key="entry.id">
        <div class="history-marker" aria-hidden="true">
          <i
            :class="['pi', entry.event_type === 'comment.created' ? 'pi-comment' : 'pi-history']"
          />
        </div>
        <div class="history-entry">
          <strong>{{ eventLabels[entry.event_type] || entry.event_type }}</strong>
          <p class="activity-author">
            {{ entry.actor.name }} ·
            <time :datetime="entry.occurred_at">{{
              formatActivityDate(entry.occurred_at, timezone)
            }}</time>
          </p>
          <template v-if="entry.event_type !== 'comment.created'"
            ><details v-for="change in entry.changes" :key="change.field" class="history-change">
              <summary>{{ fieldLabels[change.field] || change.field }}</summary>
              <dl>
                <dt>Было</dt>
                <dd>{{ historyValue(change.old_value, change.field) }}</dd>
                <dt>Стало</dt>
                <dd>{{ historyValue(change.new_value, change.field) }}</dd>
              </dl>
            </details></template
          >
        </div>
      </li>
    </ol>
    <Button
      v-if="hasMore"
      label="Загрузить следующие события"
      outlined
      :loading="loading"
      @click="history.load()"
    />
  </section>
</template>
