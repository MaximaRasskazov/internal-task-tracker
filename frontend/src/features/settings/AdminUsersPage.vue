<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { listUsers, changeRole } from '../../api/settings'
import type { User } from '../../api/types'
import { useSession } from '../../app/session'
import { useResource } from '../useResource'
import { useSettingsMutation } from './useSettingsMutation'
import { useSettingsGuard } from './useSettingsGuard'
import MutationStatus from './MutationStatus.vue'
import PageState from '../../components/PageState.vue'
import PaginationBar from '../../components/PaginationBar.vue'
const session = useSession(),
  query = ref(''),
  search = ref(''),
  offset = ref(0)
const allowed = computed(() => session.user?.role === 'admin')
const users = useResource(
  () => `${allowed.value}:${search.value}:${offset.value}`,
  (s) =>
    allowed.value
      ? listUsers(search.value, offset.value, s)
      : Promise.reject(new Error('Доступ только для администратора.')),
)
async function reload() {
  await users.reload()
  return !!users.data.value
}
const mutation = useSettingsMutation(() => allowed.value, reload)
const { busy, disabled, error, notice, blocked, verified } = mutation
useSettingsGuard(
  () => false,
  () => busy.value,
)
const roles = { developer: 'Участник команды', pm: 'Руководитель', admin: 'Администратор' }
function find() {
  search.value = query.value.trim()
  offset.value = 0
}
function setRole(user: User, event: Event) {
  const control = event.target as HTMLSelectElement
  const role = control.value as User['role']
  control.value = user.role
  if (user.id === session.user?.id || role === user.role) return
  if (
    window.confirm(
      `Изменить роль ${user.name} на «${roles[role]}»? Это изменит права пользователя во всей системе.`,
    )
  )
    void mutation.run(() => changeRole(user.id, role))
}
</script>
<template>
  <h1>Пользователи и роли</h1>
  <p>Роли определяют права во всей системе. Свою роль менять нельзя.</p>
  <template v-if="allowed"
    ><form class="settings-inline" @submit.prevent="find">
      <label class="field">Имя или email<InputText v-model="query" maxlength="254" /></label
      ><Button type="submit" label="Найти" :disabled="busy" />
    </form>
    <MutationStatus
      :error="error"
      :notice="notice"
      :blocked="blocked"
      :verified="verified"
      :busy="busy"
      @verify="mutation.verify"
      @acknowledge="mutation.acknowledge"
    />
    <PageState
      v-if="users.loading.value || users.error.value"
      :loading="users.loading.value"
      :error="users.error.value"
      @retry="reload"
    />
    <p v-else-if="!users.data.value?.items.length">Пользователи не найдены.</p>
    <ul v-else class="settings-list">
      <li v-for="user in users.data.value.items" :key="user.id">
        <div>
          <strong>{{ user.name }}</strong
          ><small>{{ user.email }} · {{ user.is_active ? 'Активен' : 'Неактивен' }}</small>
        </div>
        <label class="field"
          >Роль<select
            :value="user.role"
            :aria-label="`Роль ${user.name}`"
            :disabled="disabled || user.id === session.user?.id"
            @change="setRole(user, $event)"
          >
            <option v-for="(label, role) in roles" :key="role" :value="role">{{ label }}</option>
          </select></label
        >
      </li>
    </ul>
    <PaginationBar
      v-if="users.data.value"
      :offset="offset"
      :total="users.data.value.total"
      :limit="20"
      @change="offset = $event"
    />
  </template>
  <p v-else role="alert">Доступ только для администратора.</p>
</template>
