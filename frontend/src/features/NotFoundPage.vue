<script setup lang="ts">
import PageState from '../components/PageState.vue'
</script>
<template>
  <PageState
    title="Страница не найдена"
    description="Возможно, адрес изменился или ссылка содержит ошибку."
    ><RouterLink class="text-link" to="/projects">Вернуться к проектам</RouterLink></PageState
  >
</template>
