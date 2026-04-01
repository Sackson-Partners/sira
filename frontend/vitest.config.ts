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
      VITE_SUPABASE_URL: 'https://test-placeholder.supabase.co',
      VITE_SUPABASE_ANON_KEY: 'test-anon-key-for-testing-only',
      VITE_API_URL: '',
      VITEST: 'true',
    },
  },
})
