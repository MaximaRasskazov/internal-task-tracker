<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './AppLayout.vue'
const route = useRoute()
const isPublic = computed(() => route.meta.public)
</script>
<template>
  <RouterView v-if="isPublic" :key="route.path" /><AppLayout v-else
    ><RouterView :key="route.path"
  /></AppLayout>
</template>
