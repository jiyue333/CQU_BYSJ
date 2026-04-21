import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const backendPort = process.env.PORT ?? '8000'
const frontendPort = Number(process.env.FRONTEND_PORT ?? '3000')
const frontendHost = process.env.FRONTEND_HOST ?? '0.0.0.0'
const apiTarget = process.env.VITE_API_URL ?? `http://localhost:${backendPort}`

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: frontendHost,
    port: frontendPort,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        ws: true
      },
      '/downloads': {
        target: apiTarget,
        changeOrigin: true
      }
    }
  }
})
