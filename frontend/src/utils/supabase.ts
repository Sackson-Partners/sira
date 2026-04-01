import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// Detect test environment across all execution contexts:
//   - import.meta.env.VITEST set by Vitest at runtime
//   - globalThis.process.env.VITEST set by CI runner env vars (belt+suspenders)
//   - globalThis.process.env.NODE_ENV === 'test' set by jest-compatible runners
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const _proc = (globalThis as any).process
const isTestEnv =
  import.meta.env.VITEST === 'true' ||
  import.meta.env.MODE === 'test' ||
  _proc?.env?.['VITEST'] === 'true' ||
  _proc?.env?.['NODE_ENV'] === 'test'

const resolvedUrl = supabaseUrl && !supabaseUrl.includes('placeholder')
  ? supabaseUrl
  : isTestEnv
    ? 'https://placeholder-for-tests.supabase.co'
    : null

const resolvedKey = supabaseAnonKey && supabaseAnonKey.length > 10
  ? supabaseAnonKey
  : isTestEnv
    ? 'placeholder-anon-key-for-tests-only'
    : null

// M6: fail loudly in production — a misconfigured Supabase client silently lets
// all auth calls hit a placeholder project, making login appear broken.
if (!resolvedUrl || !resolvedKey) {
  throw new Error(
    '[SIRA] VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set. ' +
    'Copy .env.example to .env.local and fill in your Supabase project values, ' +
    'or run `vercel env pull .env.local` to sync them from Vercel.'
  )
}

export const supabase = createClient(resolvedUrl, resolvedKey)
export default supabase
