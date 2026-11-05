<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import TaskComments from './TaskComments.vue'
import TaskHistory from './TaskHistory.vue'
defineProps<{ taskId: string; timezone: string; revision: number; disabled?: boolean }>()
defineEmits<{ saved: [revision: number]; state: [draft: boolean, busy: boolean] }>()
const view = ref('comments')
</script>
<template>
  <section class="task-activity">
    <div class="activity-switch" aria-label="Раздел карточки">
      <Button
        label="Обсуждение"
        icon="pi pi-comments"
        :outlined="view !== 'comments'"
        :aria-pressed="view === 'comments'"
        @click="view = 'comments'"
      /><Button
        label="История"
        icon="pi pi-history"
        :outlined="view !== 'history'"
        :aria-pressed="view === 'history'"
        @click="view = 'history'"
      />
    </div>
    <TaskComments
      v-show="view === 'comments'"
      :task-id="taskId"
      :timezone="timezone"
      :revision="revision"
      :disabled="disabled"
      @saved="$emit('saved', $event)"
      @state="(draft, busy) => $emit('state', draft, busy)"
    /><TaskHistory
      v-show="view === 'history'"
      :task-id="taskId"
      :timezone="timezone"
      :revision="revision"
    />
  </section>
</template>
