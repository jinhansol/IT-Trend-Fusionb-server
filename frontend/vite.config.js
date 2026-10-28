import process from 'node:process'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // DevHub 2.0 backend (uv run uvicorn app.main:create_app --factory) for local dev.
  // Requests to /api go through this proxy, so the browser sees a single origin.
  const apiTarget = env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': { target: apiTarget, changeOrigin: false },
      },
    },
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{js,jsx}'],
    },
  }
})
