<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { readTask } from '../../api/tasks'
import { listHistory } from '../../api/activity'
import { ApiError, errorMessage } from '../../api/client'
import PageState from '../../components/PageState.vue'
import TaskHistory from './TaskHistory.vue'
const route = useRoute()
const router = useRouter()
const error = ref('')
const loading = ref(true)
const historical = ref(false)
const controller = new AbortController()
async function load() {
  loading.value = true
  error.value = ''
  historical.value = false
  try {
    const { data } = await readTask(String(route.params.taskId), controller.signal)
    if (!controller.signal.aborted)
      await router.replace({
        path: `/projects/${data.project_id}/boards/${data.board_id}`,
        query: { task: data.id },
      })
  } catch (e) {
    if (controller.signal.aborted) return
    if (e instanceof ApiError && e.status === 404) {
      try {
        await listHistory(String(route.params.taskId), 0, controller.signal)
        if (!controller.signal.aborted) historical.value = true
      } catch {
        if (!controller.signal.aborted) error.value = 'Задача недоступна.'
      }
    } else error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
onUnmounted(() => controller.abort())
</script>
<template>
  <template v-if="historical"
    ><h1>История удалённой задачи</h1>
    <p class="muted">Задача недоступна для редактирования. Время событий показано в UTC.</p>
    <TaskHistory :task-id="String(route.params.taskId)" /></template
  ><PageState v-else :loading="loading" :error="error" @retry="load" /><RouterLink
    class="back-link"
    to="/projects"
    >К проектам</RouterLink
  >
</template>
