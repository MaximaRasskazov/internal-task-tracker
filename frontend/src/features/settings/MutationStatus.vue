<script setup lang="ts">
import Button from 'primevue/button'
import FormError from '../../components/FormError.vue'
defineProps<{
  error: unknown
  notice: string
  blocked: boolean
  verified: boolean
  busy: boolean
}>()
defineEmits<{ verify: []; acknowledge: [] }>()
</script>
<template>
  <FormError :error="error" />
  <p v-if="notice" class="info-banner" role="status">{{ notice }}</p>
  <div v-if="blocked" class="info-banner">
    <p>
      Проверьте актуальные данные: операция могла сохраниться или данные изменились. Автоматического
      повтора нет.
    </p>
    <Button label="Обновить данные" outlined :loading="busy" @click="$emit('verify')" /><Button
      v-if="verified"
      label="Проверил: разрешить новую операцию"
      text
      :disabled="busy"
      @click="$emit('acknowledge')"
    />
  </div>
</template>
