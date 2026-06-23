import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const API_TARGET = env.VITE_API_BASE || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    build: {
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
          dashboard: resolve(__dirname, 'dashboard.html'),
        },
      },
    },
    server: {
      port: 5173,
      host: '127.0.0.1',
      proxy: {
        '/api': { target: API_TARGET, changeOrigin: true, secure: false },
        '/admin': { target: API_TARGET, changeOrigin: true, secure: false },
        '/webhooks': { target: API_TARGET, changeOrigin: true, secure: false },
      },
    },
  }
})
