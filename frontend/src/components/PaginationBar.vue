<script setup lang="ts">
import Button from 'primevue/button'
defineProps<{ offset: number; total: number; limit: number }>()
defineEmits<{ change: [offset: number] }>()
</script>
<template>
  <nav v-if="total > limit" class="pagination" aria-label="Страницы списка">
    <Button
      icon="pi pi-arrow-left"
      label="Назад"
      outlined
      :disabled="offset === 0"
      @click="$emit('change', Math.max(0, offset - limit))"
    /><span>{{ offset + 1 }}–{{ Math.min(offset + limit, total) }} из {{ total }}</span
    ><Button
      icon="pi pi-arrow-right"
      icon-pos="right"
      label="Далее"
      outlined
      :disabled="offset + limit >= total"
      @click="$emit('change', offset + limit)"
    />
  </nav>
</template>
