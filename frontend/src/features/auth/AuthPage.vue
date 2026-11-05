<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import { useSession } from '../../app/session'
import { safeReturn } from '../../app/navigation'
import { ApiError, fieldError } from '../../api/client'
import FormError from '../../components/FormError.vue'
const route = useRoute()
const router = useRouter()
const session = useSession()
const registration = computed(() => route.path === '/register')
const form = reactive({ name: '', email: '', password: '', confirmation: '' })
const busy = ref(false)
const error = ref<unknown>(null)
const cooldown = ref(0)
const timer = window.setInterval(() => {
  if (cooldown.value > 0) cooldown.value--
}, 1000)
onUnmounted(() => window.clearInterval(timer))
async function submit() {
  if (busy.value || cooldown.value) return
  error.value = null
  if (registration.value && form.password !== form.confirmation) {
    error.value = new Error('Пароли не совпадают.')
    return
  }
  busy.value = true
  try {
    if (registration.value) {
      await session.register({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      })
      await router.replace({ path: '/login', query: { registered: '1' } })
    } else {
      await session.login({ email: form.email.trim(), password: form.password })
      await router.replace(safeReturn(route.query.returnTo))
    }
  } catch (e) {
    error.value = e
    if (e instanceof ApiError && e.status === 429) cooldown.value = e.retryAfter || 60
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <main class="auth-page">
    <section class="auth-story">
      <div class="brand">
        <span class="brand-icon"><i class="pi pi-th-large" /></span>Трекер
      </div>
      <div class="auth-copy">
        <span class="eyebrow">МЕНЬШЕ СУЕТЫ. БОЛЬШЕ РЕЗУЛЬТАТА.</span>
        <h1>Есть идея?<br />Давайте <em>сделаем.</em></h1>
        <p>Проекты, задачи и команда —<br />в одном понятном пространстве.</p>
        <div class="abstract-board" aria-hidden="true">
          <div>
            <span class="mini-label">В планах</span>
            <div class="mini-card peach">
              <span>✦</span> Свежие идеи
              <div class="mini-line" />
            </div>
            <div class="mini-card">
              <div class="mini-line" />
              <div class="mini-line short" />
            </div>
          </div>
          <div>
            <span class="mini-label">В работе</span>
            <div class="mini-card lavender">
              <span>↗</span> Общая цель
              <div class="mini-line" />
            </div>
          </div>
          <div>
            <span class="mini-label">Готово</span>
            <div class="mini-card mint">
              <span>✓</span> Первый шаг
              <div class="mini-line" />
            </div>
          </div>
        </div>
      </div>
      <small>От первого шага до общего результата.</small>
    </section>
    <section class="auth-form-side">
      <form class="auth-form" @submit.prevent="submit">
        <span class="eyebrow">ВАШЕ РАБОЧЕЕ ПРОСТРАНСТВО</span>
        <h2>{{ registration ? 'Начнём знакомство' : 'С возвращением!' }}</h2>
        <p class="muted">
          {{
            registration
              ? 'Создайте аккаунт и присоединитесь к команде.'
              : 'Войдите, чтобы продолжить работу с командой.'
          }}
        </p>
        <p v-if="route.query.registered" class="success-banner" role="status">
          Аккаунт создан. Теперь войдите.
        </p>
        <p v-if="route.query.unavailable" class="error-banner">
          Сервер недоступен. После запуска бэкенда попробуйте войти.
        </p>
        <label v-if="registration" class="field"
          >Ваше имя<InputText
            v-model="form.name"
            autocomplete="name"
            required
            maxlength="80"
            :invalid="!!fieldError(error, 'name')"
          /><small class="field-error">{{ fieldError(error, 'name') }}</small></label
        >
        <label class="field"
          >Электронная почта<InputText
            v-model="form.email"
            type="email"
            autocomplete="username"
            placeholder="name@company.ru"
            required
            maxlength="254"
            :invalid="!!fieldError(error, 'email')"
          /><small class="field-error">{{ fieldError(error, 'email') }}</small></label
        >
        <div class="field">
          <label for="password">Пароль</label
          ><Password
            v-model="form.password"
            input-id="password"
            :feedback="false"
            toggle-mask
            :input-props="{
              required: true,
              minlength: 12,
              maxlength: 128,
              autocomplete: registration ? 'new-password' : 'current-password',
            }"
            :invalid="!!fieldError(error, 'password')"
            fluid
          /><small v-if="registration" class="muted">От 12 до 128 символов</small
          ><small class="field-error">{{ fieldError(error, 'password') }}</small>
        </div>
        <div v-if="registration" class="field">
          <label for="confirmation">Повторите пароль</label
          ><Password
            v-model="form.confirmation"
            input-id="confirmation"
            :feedback="false"
            toggle-mask
            :input-props="{ required: true, autocomplete: 'new-password' }"
            fluid
          />
        </div>
        <FormError :error="error" /><Button
          type="submit"
          class="auth-submit"
          :label="
            cooldown
              ? `Повторить через ${cooldown} с`
              : registration
                ? 'Создать аккаунт'
                : 'Войти в пространство'
          "
          icon="pi pi-arrow-right"
          icon-pos="right"
          :loading="busy"
          :disabled="cooldown > 0"
        />
        <p class="auth-switch">
          {{ registration ? 'Уже с нами?' : 'Первый раз здесь?' }}
          <RouterLink :to="registration ? '/login' : '/register'">{{
            registration ? 'Войти' : 'Создать аккаунт'
          }}</RouterLink>
        </p>
      </form>
      <small class="auth-footer">Internal Task Tracker · Вместе получается больше</small>
    </section>
  </main>
</template>
