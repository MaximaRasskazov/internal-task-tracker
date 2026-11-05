<script setup lang="ts">
import Button from 'primevue/button'
defineProps<{
  loading?: boolean
  error?: string
  title?: string
  description?: string
  icon?: string
}>()
defineEmits<{ retry: [] }>()
</script>
<template>
  <section class="page-state" :role="error ? 'alert' : 'status'" :aria-busy="loading">
    <i
      :class="[
        'pi',
        loading ? 'pi-spin pi-spinner' : error ? 'pi-exclamation-circle' : icon || 'pi-folder-open',
      ]"
      aria-hidden="true"
    />
    <h2>
      {{ loading ? 'Загружаем пространство…' : error ? 'Не удалось загрузить данные' : title }}
    </h2>
    <p>{{ error || description }}</p>
    <Button
      v-if="error"
      label="Повторить"
      icon="pi pi-refresh"
      outlined
      @click="$emit('retry')"
    /><slot v-else-if="!loading" />
  </section>
</template>
