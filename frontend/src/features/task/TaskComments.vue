<script setup lang="ts">
import { onMounted, computed, watch } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import FormError from '../../components/FormError.vue'
import PaginationBar from '../../components/PaginationBar.vue'
import { useComments } from './useComments'
import { formatActivityDate } from './history-format'
const props = defineProps<{
  taskId: string
  timezone: string
  revision: number
  disabled?: boolean
}>()
const emit = defineEmits<{ saved: [revision: number]; state: [draft: boolean, busy: boolean] }>()
const comments = useComments(props.taskId, (revision) => emit('saved', revision))
const {
  draft,
  busy,
  uncertain,
  verified,
  error,
  readError,
  page,
  offset,
  loading,
  sent,
  unavailable,
} = comments
const recent = computed(() =>
  sent.value && !page.value?.items.some((i) => i.id === sent.value?.id) ? sent.value : null,
)
watch([draft, busy], () => emit('state', !!draft.value.trim(), busy.value), { immediate: true })
watch(
  () => props.revision,
  () => {
    if (!busy.value) void comments.load()
  },
)
onMounted(() => comments.load())
function retry() {
  if (
    window.confirm(
      'Проверьте последние страницы обсуждения. Повторить отправку? Если комментарий уже сохранён, появится дубликат.',
    )
  )
    comments.allowRetry()
}
function submit() {
  if (!props.disabled) void comments.send()
}
function shortcut(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing) {
    event.preventDefault()
    if (!props.disabled) void comments.send()
  }
}
</script>
<template>
  <section class="activity-section" aria-label="Комментарии">
    <div class="section-heading">
      <h3>
        Обсуждение <span class="count-pill">{{ page?.total || 0 }}</span>
      </h3>
      <Button
        label="Обновить"
        icon="pi pi-refresh"
        text
        :loading="loading"
        @click="comments.load()"
      />
    </div>
    <FormError :error="readError" /><Button
      v-if="readError"
      label="Повторить загрузку"
      outlined
      @click="comments.load()"
    />
    <p v-if="loading" role="status">Загружаем комментарии…</p>
    <p v-else-if="!page?.items.length && !readError" class="muted">
      Начните обсуждение: задайте вопрос или поделитесь результатом.
    </p>
    <ol class="comment-list">
      <li v-for="comment in page?.items" :key="comment.id">
        <div class="comment-header">
          <span class="avatar">{{ comment.author.name.slice(0, 1) }}</span>
          <div>
            <strong>{{ comment.author.name }}</strong
            ><time :datetime="comment.created_at">{{
              formatActivityDate(comment.created_at, timezone)
            }}</time>
          </div>
        </div>
        <p class="comment-text">{{ comment.text }}</p>
      </li>
    </ol>
    <PaginationBar
      v-if="page"
      :offset="offset"
      :total="page.total"
      :limit="20"
      @change="comments.load($event)"
    />
    <aside v-if="recent" class="sent-comment" role="status">
      <strong>Ваш комментарий отправлен</strong>
      <p class="comment-text">{{ recent.text }}</p>
      <small>Он находится на одной из следующих страниц обсуждения.</small>
    </aside>
    <form class="comment-compose" @submit.prevent="submit">
      <label class="field"
        >Ваш комментарий<Textarea
          v-model="draft"
          rows="4"
          maxlength="5000"
          auto-resize
          :disabled="busy || disabled || unavailable"
          placeholder="Что важно знать команде?"
          @keydown="shortcut"
      /></label>
      <div class="comment-hint">
        <small>Ctrl/⌘ + Enter — отправить</small><small>{{ draft.length }} / 5000</small>
      </div>
      <FormError :error="error" />
      <div v-if="uncertain" class="info-banner">
        <p>
          Неизвестно, сохранился ли комментарий. Текст оставлен в форме. Обновите обсуждение и
          проверьте последние страницы.
        </p>
        <Button
          label="Обновить обсуждение"
          outlined
          :loading="loading"
          @click="comments.load()"
        /><Button
          v-if="verified"
          label="Проверил: разрешить повторную отправку"
          text
          @click="retry"
        />
      </div>
      <Button
        type="submit"
        label="Отправить"
        icon="pi pi-send"
        :loading="busy"
        :disabled="disabled || unavailable || uncertain || !draft.trim()"
      />
    </form>
  </section>
</template>
