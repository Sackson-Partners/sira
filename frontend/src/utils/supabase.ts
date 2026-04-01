import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// M6: fail loudly — a misconfigured Supabase client silently lets all auth calls
// hit a placeholder project, making login appear broken without a clear error.
// Skip the guard in test environments where env vars are intentionally absent.
const isTestEnv = import.meta.env.VITEST === 'true' || import.meta.env.MODE === 'test'

if (!isTestEnv) {
  if (!supabaseUrl || supabaseUrl.includes('placeholder') || !supabaseAnonKey || supabaseAnonKey.includes('placeholder')) {
    throw new Error(
      '[SIRA] VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set. ' +
      'Copy .env.example to .env.local and fill in your Supabase project values, ' +
      'or run `vercel env pull .env.local` to sync them from Vercel.'
    )
  }
}

const url = supabaseUrl || 'https://test-placeholder.supabase.co'
const key = supabaseAnonKey || 'test-placeholder-key'

export const supabase = createClient(url, key)
