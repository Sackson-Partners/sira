import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      reporter: ['text', 'json', 'html'],
    },
    env: {
      VITEST: 'true',
      VITE_SUPABASE_URL: 'https://placeholder-for-tests.supabase.co',
      VITE_SUPABASE_ANON_KEY: 'placeholder-anon-key-for-tests-only',
      VITE_API_URL: '',
      NODE_ENV: 'test',
    },
  },
})
