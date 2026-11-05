<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import { getProject, listMembers } from '../../api/projects'
import {
  patchProject,
  deleteProject,
  addMember,
  removeMember,
  changeOwner,
  manages,
} from '../../api/settings'
import type { Member } from '../../api/types'
import { useSession } from '../../app/session'
import { useResource } from '../useResource'
import { useSettingsMutation } from './useSettingsMutation'
import { useSettingsGuard } from './useSettingsGuard'
import MutationStatus from './MutationStatus.vue'
import PageState from '../../components/PageState.vue'
import PaginationBar from '../../components/PaginationBar.vue'
const route = useRoute(),
  router = useRouter(),
  session = useSession()
const id = String(route.params.projectId),
  offset = ref(0)
const project = useResource(
  () => id,
  (s) => getProject(id, s),
)
const members = useResource(
  () => `${id}:${offset.value}`,
  (s) => listMembers(id, offset.value, s),
)
const name = ref(''),
  description = ref(''),
  baseName = ref(''),
  baseDescription = ref(''),
  email = ref('')
const dirty = computed(
  () =>
    name.value !== baseName.value || description.value !== baseDescription.value || !!email.value,
)
watch(project.data, (p) => {
  if (p && !dirty.value) {
    name.value = baseName.value = p.name
    description.value = baseDescription.value = p.description
  }
})
const allowed = computed(() => manages(session.user, project.data.value?.owner_id))
async function reload() {
  await Promise.all([project.reload(), members.reload()])
  return !!project.data.value && !!members.data.value
}
const mutation = useSettingsMutation(() => allowed.value, reload)
const { busy, disabled, error, notice, blocked, verified } = mutation
useSettingsGuard(
  () => dirty.value,
  () => busy.value,
)
function save() {
  if (!name.value.trim()) return
  void mutation.run(
    () => patchProject(id, { name: name.value.trim(), description: description.value }),
    () => {
      baseName.value = name.value = name.value.trim()
      baseDescription.value = description.value
    },
  )
}
function add() {
  if (!email.value.trim()) return
  void mutation.run(
    () => addMember(id, email.value.trim()),
    () => {
      email.value = ''
    },
  )
}
function remove(member: Member) {
  if (
    !member.is_owner &&
    window.confirm(`Удалить ${member.name} из проекта? Доступ к доскам будет закрыт.`)
  )
    void mutation.run(() => removeMember(id, member.user_id))
}
function transfer(member: Member) {
  if (
    member.is_active &&
    !member.is_owner &&
    window.confirm(
      `Передать руководство проекта пользователю ${member.name}? Ваши права управления могут измениться.`,
    )
  )
    void mutation.run(() => changeOwner(id, member.user_id))
}
async function removeProject() {
  if (
    window.confirm(
      'Удалить проект? Сервер разрешит удаление только после удаления его досок и тегов.',
    )
  ) {
    const done = await mutation.run(
      () => deleteProject(id),
      () => {
        name.value = baseName.value
        description.value = baseDescription.value
        email.value = ''
      },
    )
    if (done) await router.replace('/projects')
  }
}
</script>
<template>
  <RouterLink class="back-link" :to="`/projects/${id}`">К проекту</RouterLink>
  <h1>Настройки проекта</h1>
  <PageState
    v-if="!project.data.value"
    :loading="project.loading.value"
    :error="project.error.value"
    @retry="reload"
  />
  <template v-else-if="allowed">
    <MutationStatus
      :error="error"
      :notice="notice"
      :blocked="blocked"
      :verified="verified"
      :busy="busy"
      @verify="mutation.verify"
      @acknowledge="mutation.acknowledge"
    />
    <section class="settings-section">
      <h2>Основные данные</h2>
      <p class="muted">
        Ключ {{ project.data.value.key }} · Часовой пояс {{ project.data.value.timezone }}. Эти
        параметры заданы при создании.
      </p>
      <form class="stack-form" @submit.prevent="save">
        <label class="field"
          >Название<InputText v-model="name" required maxlength="100" :disabled="busy" /></label
        ><label class="field"
          >Описание<Textarea
            v-model="description"
            rows="4"
            maxlength="2000"
            :disabled="busy" /></label
        ><Button type="submit" label="Сохранить проект" :disabled="disabled || !name.trim()" />
      </form>
    </section>
    <section class="settings-section">
      <h2>Участники</h2>
      <form class="settings-inline" @submit.prevent="add">
        <label class="field"
          >Email зарегистрированного пользователя<InputText
            v-model="email"
            type="email"
            required
            maxlength="254"
            :disabled="busy" /></label
        ><Button type="submit" label="Добавить" :disabled="disabled" />
      </form>
      <PageState
        v-if="members.loading.value || members.error.value"
        :loading="members.loading.value"
        :error="members.error.value"
        @retry="members.reload"
      />
      <ul v-else class="settings-list">
        <li v-for="member in members.data.value?.items" :key="member.user_id">
          <div>
            <strong>{{ member.name }}</strong
            ><small>{{
              member.is_owner ? 'Руководитель' : member.is_active ? 'Участник' : 'Неактивен'
            }}</small>
          </div>
          <div class="task-actions">
            <Button
              v-if="!member.is_owner && member.is_active"
              label="Сделать руководителем"
              text
              :disabled="disabled"
              @click="transfer(member)"
            /><Button
              v-if="!member.is_owner"
              label="Удалить участника"
              severity="danger"
              text
              :disabled="disabled"
              @click="remove(member)"
            />
          </div>
        </li>
      </ul>
      <PaginationBar
        v-if="members.data.value"
        :offset="offset"
        :total="members.data.value.total"
        :limit="12"
        @change="offset = $event"
      />
    </section>
    <section class="settings-section">
      <h2>Удаление проекта</h2>
      <p>Сначала нужно удалить все доски и теги проекта.</p>
      <Button
        label="Удалить проект"
        severity="danger"
        outlined
        :disabled="disabled"
        @click="removeProject"
      />
    </section>
  </template>
  <p v-else role="alert">Настройки доступны руководителю проекта и администратору.</p>
</template>
