import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Belt+suspenders: stamp process.env before any module evaluates.
// vitest.config.ts `env` sets import.meta.env; this covers process.env
// fallback path used by supabase.ts in CI runners without Vitest globals.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const proc = (globalThis as any).process
if (proc?.env) {
  proc.env['VITEST'] = 'true'
  proc.env['NODE_ENV'] = 'test'
  proc.env['VITE_SUPABASE_URL'] = 'https://placeholder-for-tests.supabase.co'
  proc.env['VITE_SUPABASE_ANON_KEY'] = 'placeholder-anon-key-for-tests-only'
}

// Global supabase mock — prevents any real network call in tests.
// Both path aliases cover barrel imports and direct relative imports.
const supabaseMock = {
  auth: {
    getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
    onAuthStateChange: vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    }),
    signInWithPassword: vi.fn().mockResolvedValue({
      data: { user: null, session: null },
      error: null,
    }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
    refreshSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
  },
}

vi.mock('@/utils/supabase', () => ({ default: supabaseMock, supabase: supabaseMock }))
vi.mock('../utils/supabase', () => ({ default: supabaseMock, supabase: supabaseMock }))
vi.mock('../../utils/supabase', () => ({ default: supabaseMock, supabase: supabaseMock }))
