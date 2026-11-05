<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import { getProject, listBoards, listMembers, createBoard } from '../../api/projects'
import { useSession } from '../../app/session'
import { useResource } from '../useResource'
import PageState from '../../components/PageState.vue'
import FormError from '../../components/FormError.vue'
import { useCreation } from './useCreation'
import { useSettingsGuard } from '../settings/useSettingsGuard'
import PaginationBar from '../../components/PaginationBar.vue'
const route = useRoute()
const router = useRouter()
const session = useSession()
const id = computed(() => String(route.params.projectId))
const boardOffset = ref(0)
const memberOffset = ref(0)
const project = useResource(
  () => id.value,
  (s) => getProject(id.value, s),
)
const boards = useResource(
  () => `${id.value}:${boardOffset.value}`,
  (s) => listBoards(id.value, boardOffset.value, s),
)
const members = useResource(
  () => `${id.value}:${memberOffset.value}`,
  (s) => listMembers(id.value, memberOffset.value, s),
)
const canManage = computed(
  () => session.user?.role === 'admin' || session.user?.id === project.data.value?.owner_id,
)
const creating = ref(false)
const name = ref('')
const creation = useCreation()
const { busy, blocked, error } = creation
useSettingsGuard(
  () => !!name.value,
  () => busy.value,
)
async function submit() {
  if (!canManage.value || !name.value.trim()) return
  await creation.run(
    () => createBoard(id.value, name.value.trim()),
    (board) => {
      creating.value = false
      name.value = ''
      void router.push(`/projects/${id.value}/boards/${board.id}`)
    },
  )
}
</script>
<template>
  <RouterLink class="back-link" to="/projects"
    ><i class="pi pi-arrow-left" /> Все проекты</RouterLink
  ><PageState
    v-if="project.loading.value || project.error.value"
    :loading="project.loading.value"
    :error="project.error.value"
    @retry="project.reload"
  /><template v-else-if="project.data.value"
    ><div class="page-heading">
      <div>
        <span class="eyebrow">ПРОЕКТ · {{ project.data.value.key }}</span>
        <h1>{{ project.data.value.name }}</h1>
        <p>
          {{
            project.data.value.description || 'Задачи, идеи и люди, которые воплощают их в жизнь.'
          }}
        </p>
      </div>
      <RouterLink :to="`/projects/${id}/analytics`" class="back-link">Аналитика проекта</RouterLink>
      <RouterLink v-if="canManage" :to="`/projects/${id}/settings`" class="back-link"
        >Настройки проекта</RouterLink
      >
      <Button v-if="canManage" label="Новая доска" icon="pi pi-plus" @click="creating = true" />
    </div>
    <div class="project-detail-grid">
      <section>
        <div class="section-heading">
          <h2>Доски проекта</h2>
          <Button label="Обновить" text :loading="boards.loading.value" @click="boards.reload" />
          <span class="count-pill">{{ boards.data.value?.total || 0 }}</span>
        </div>
        <PageState
          v-if="boards.loading.value || boards.error.value"
          :loading="boards.loading.value"
          :error="boards.error.value"
          @retry="boards.reload"
        /><PageState
          v-else-if="!boards.data.value?.items.length"
          title="Пока нет досок"
          description="Доска помогает разложить работу по этапам."
        />
        <div v-else class="board-list">
          <RouterLink
            v-for="board in boards.data.value.items"
            :key="board.id"
            :to="`/projects/${id}/boards/${board.id}`"
            class="board-link"
            ><span class="board-icon"><i class="pi pi-objects-column" /></span>
            <div>
              <h3>{{ board.name }}</h3>
              <span class="muted">Открыть задачи проекта</span>
            </div>
            <i class="pi pi-arrow-right"
          /></RouterLink>
        </div>
        <PaginationBar
          v-if="boards.data.value"
          :offset="boardOffset"
          :total="boards.data.value.total"
          :limit="12"
          @change="boardOffset = $event"
        />
      </section>
      <section class="members-panel">
        <div class="section-heading">
          <h2>Команда</h2>
          <span class="count-pill">{{ members.data.value?.total || 0 }}</span>
        </div>
        <PageState
          v-if="members.loading.value || members.error.value"
          :loading="members.loading.value"
          :error="members.error.value"
          @retry="members.reload"
        />
        <ul v-else class="member-list">
          <li v-for="member in members.data.value?.items" :key="member.user_id">
            <span class="avatar">{{ member.name.slice(0, 1) }}</span>
            <div>
              <strong>{{ member.name }}</strong
              ><small>{{
                member.is_owner
                  ? 'Руководитель проекта'
                  : member.is_active
                    ? 'Участник'
                    : 'Неактивен'
              }}</small>
            </div>
          </li>
        </ul>
        <PaginationBar
          v-if="members.data.value"
          :offset="memberOffset"
          :total="members.data.value.total"
          :limit="12"
          @change="memberOffset = $event"
        />
      </section></div></template
  ><Dialog
    v-model:visible="creating"
    header="Новая доска"
    modal
    :closable="!busy"
    :close-on-escape="!busy"
    :style="{ width: '28rem' }"
    :breakpoints="{ '600px': '94vw' }"
    ><form class="stack-form" @submit.prevent="submit">
      <label class="field"
        >Название доски<InputText
          v-model="name"
          :disabled="busy"
          required
          maxlength="100"
          autofocus
      /></label>
      <p class="muted">Начальные колонки появятся автоматически.</p>
      <FormError :error="error" />
      <div v-if="blocked" class="info-banner">
        <p>
          Ответ не получен. Закройте окно и обновите список досок перед повтором. Название останется
          в форме.
        </p>
        <Button label="Проверил список: разрешить повтор" text @click="creation.allowRetry" />
      </div>
      <Button label="Создать доску" type="submit" :disabled="blocked" :loading="busy" /></form
  ></Dialog>
</template>
