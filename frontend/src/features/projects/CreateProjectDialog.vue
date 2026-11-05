<script setup lang="ts">
import { reactive } from 'vue'
import { useCreation } from './useCreation'
import { useSettingsGuard } from '../settings/useSettingsGuard'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import { createProject } from '../../api/projects'
import { fieldError } from '../../api/client'
import FormError from '../../components/FormError.vue'
import type { Project } from '../../api/types'
const visible = defineModel<boolean>({ required: true })
const emit = defineEmits<{ created: [project: Project] }>()
const form = reactive({
  name: '',
  key: '',
  description: '',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
})
const creation = useCreation()
const { busy, blocked, error } = creation
useSettingsGuard(
  () => !!(form.name || form.key || form.description),
  () => busy.value,
)
async function submit() {
  await creation.run(
    () => createProject({ ...form, key: form.key.toUpperCase() }),
    (project) => {
      visible.value = false
      form.name = ''
      form.key = ''
      form.description = ''
      emit('created', project)
    },
  )
}
</script>
<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Новый проект"
    :style="{ width: '32rem' }"
    :breakpoints="{ '600px': '94vw' }"
    :closable="!busy"
    :close-on-escape="!busy"
    ><form class="stack-form" @submit.prevent="submit">
      <p class="muted">Дайте общей идее своё пространство.</p>
      <label class="field"
        >Название<InputText
          v-model="form.name"
          :disabled="busy"
          required
          maxlength="100"
          autofocus
          :invalid="!!fieldError(error, 'name')"
        /><small class="field-error">{{ fieldError(error, 'name') }}</small></label
      ><label class="field"
        >Ключ проекта<InputText
          v-model="form.key"
          :disabled="busy"
          required
          minlength="2"
          maxlength="8"
          pattern="[A-Za-z][A-Za-z0-9]{1,7}"
          placeholder="TEAM"
          :invalid="!!fieldError(error, 'key')"
        /><small class="muted"
          >2–8 латинских букв или цифр, начиная с буквы. Например, TEAM-1 станет ключом
          задачи.</small
        ><small class="field-error">{{ fieldError(error, 'key') }}</small></label
      ><label class="field"
        >Описание<Textarea
          v-model="form.description"
          :disabled="busy"
          rows="3"
          maxlength="2000"
          auto-resize /></label
      ><label class="field"
        >Часовой пояс<InputText
          v-model="form.timezone"
          :disabled="busy"
          required
          placeholder="Asia/Yekaterinburg"
          :invalid="!!fieldError(error, 'timezone')"
        /><small class="muted">Ключ и часовой пояс нельзя изменить после создания.</small
        ><small class="field-error">{{ fieldError(error, 'timezone') }}</small></label
      ><FormError :error="error" />
      <div v-if="blocked" class="info-banner">
        <p>
          Ответ не получен. Закройте окно и проверьте список проектов перед повтором. Введённые
          данные останутся в форме.
        </p>
        <Button label="Проверил список: разрешить повтор" text @click="creation.allowRetry" />
      </div>
      <div class="form-actions">
        <Button
          label="Отмена"
          text
          severity="secondary"
          :disabled="busy"
          @click="visible = false"
        /><Button label="Создать проект" type="submit" :loading="busy" :disabled="blocked" />
      </div></form
  ></Dialog>
</template>
