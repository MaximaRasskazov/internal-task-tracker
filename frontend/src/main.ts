import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import { definePreset } from '@primeuix/themes'
import App from './app/App.vue'
import { router } from './app/router'
import { useSession } from './app/session'
import { setUnauthorizedHandler } from './api/client'
import 'primeicons/primeicons.css'
import './styles/base.css'
const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(PrimeVue, {
  theme: {
    preset: definePreset(Aura, {
      semantic: {
        primary: {
          50: '{sky.50}',
          100: '{sky.100}',
          200: '{sky.200}',
          300: '{sky.300}',
          400: '{sky.400}',
          500: '{sky.700}',
          600: '{sky.800}',
          700: '{sky.900}',
          800: '{sky.800}',
          900: '{sky.900}',
          950: '{sky.950}',
        },
      },
    }),
    options: { darkModeSelector: false },
  },
})
setUnauthorizedHandler(() => {
  useSession(pinia).clear()
  if (!router.currentRoute.value.meta.public)
    void router.replace({ path: '/login', query: { returnTo: router.currentRoute.value.fullPath } })
})
app.use(router)
app.mount('#app')
