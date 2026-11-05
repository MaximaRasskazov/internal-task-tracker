import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.API_PROXY_TARGET || 'http://127.0.0.1:8000'
  return {
    plugins: [vue()],
    server: {
      host: 'localhost',
      port: 5173,
      strictPort: true,
      proxy: { '/api': { target }, '/ws': { target, ws: true } },
    },
    test: { environment: 'jsdom', clearMocks: true },
  }
})
