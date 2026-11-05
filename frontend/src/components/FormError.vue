<script setup lang="ts">
import { errorMessage } from '../api/client'
defineProps<{ error: unknown }>()
</script>
<template>
  <p v-if="error" class="form-error" role="alert">{{ errorMessage(error) }}</p>
</template>
