/**
 * SIRA Platform — Supabase Client (Phase 2)
  * Authentication: Supabase Auth with JWT + RBAC
   * Frontend: Next.js 14 (App Router) hosted on Vercel
    */

    import { createBrowserClient } from '@supabase/ssr'
    import { createServerClient } from '@supabase/ssr'
    import { cookies } from 'next/headers'
    import type { Database } from '@/types/database'

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

    // Browser client — used in React components and client hooks
    export function createClient() {
      return createBrowserClient<Database>(supabaseUrl, supabaseAnonKey)
      }

      // Server client — used in Server Components, Route Handlers, Server Actions
      export async function createServerSupabaseClient() {
        const cookieStore = await cookies()
          return createServerClient<Database>(supabaseUrl, supabaseAnonKey, {
              cookies: {
                    getAll() {
                            return cookieStore.getAll()
                                  },
                                        setAll(cookiesToSet) {
                                                try {
                                                          cookiesToSet.forEach(({ name, value, options }) =>
                                                                      cookieStore.set(name, value, options)
                                                                                )
                                                                                        } catch {
                                                                                                  // Server component — cookie mutations handled by middleware
                                                                                                          }
                                                                                                                },
                                                                                                                    },
                                                                                                                      })
                                                                                                                      }
                                                                                                                      
                                                                                                                      // Shared singleton for client components
                                                                                                                      export const supabase = createClient()
                                                                                                                      
                                                                                                                      // ---------------------------------------------------------------------------
                                                                                                                      // Auth helpers
                                                                                                                      // ---------------------------------------------------------------------------
                                                                                                                      
                                                                                                                      export async function signInWithEmail(email: string, password: string) {
                                                                                                                        const client = createClient()
                                                                                                                          return client.auth.signInWithPassword({ email, password })
                                                                                                                          }
                                                                                                                          
                                                                                                                          export async function signUpWithEmail(email: string, password: string, fullName: string) {
                                                                                                                            const client = createClient()
                                                                                                                              return client.auth.signUp({
                                                                                                                                  email,
                                                                                                                                      password,
                                                                                                                                          options: { data: { full_name: fullName } },
                                                                                                                                            })
                                                                                                                                            }
                                                                                                                                            
                                                                                                                                            export async function signOut() {
                                                                                                                                              const client = createClient()
                                                                                                                                                return client.auth.signOut()
                                                                                                                                                }
                                                                                                                                                
                                                                                                                                                export async function getCurrentUser() {
                                                                                                                                                  const client = createClient()
                                                                                                                                                    const { data: { user } } = await client.auth.getUser()
                                                                                                                                                      return user
                                                                                                                                                      }
                                                                                                                                                      
                                                                                                                                                      export async function getCurrentSession() {
                                                                                                                                                        const client = createClient()
                                                                                                                                                          const { data: { session } } = await client.auth.getSession()
                                                                                                                                                            return session
                                                                                                                                                            }
                                                                                                                                                            
                                                                                                                                                            // ---------------------------------------------------------------------------
                                                                                                                                                            // User profile helpers
                                                                                                                                                            // ---------------------------------------------------------------------------
                                                                                                                                                            
                                                                                                                                                            export async function getUserProfile(userId: string) {
                                                                                                                                                              const client = createClient()
                                                                                                                                                                const { data, error } = await client
                                                                                                                                                                    .from('users')
                                                                                                                                                                        .select('*, organisations(*)')
                                                                                                                                                                            .eq('id', userId)
                                                                                                                                                                                .single()
                                                                                                                                                                                  if (error) throw error
                                                                                                                                                                                    return data
                                                                                                                                                                                    }
                                                                                                                                                                                    
                                                                                                                                                                                    export async function updateUserProfile(userId: string, updates: Partial<{
                                                                                                                                                                                      full_name: string
                                                                                                                                                                                        phone: string
                                                                                                                                                                                          avatar_url: string
                                                                                                                                                                                          }>) {
                                                                                                                                                                                            const client = createClient()
                                                                                                                                                                                              const { data, error } = await client
                                                                                                                                                                                                  .from('users')
                                                                                                                                                                                                      .update(updates)
                                                                                                                                                                                                          .eq('id', userId)
                                                                                                                                                                                                              .select()
                                                                                                                                                                                                                  .single()
                                                                                                                                                                                                                    if (error) throw error
                                                                                                                                                                                                                      return data
                                                                                                                                                                                                                      }
                                                                                                                                                                                                                      
                                                                                                                                                                                                                      // ---------------------------------------------------------------------------
                                                                                                                                                                                                                      // RBAC role check helpers
                                                                                                                                                                                                                      // ---------------------------------------------------------------------------
                                                                                                                                                                                                                      
                                                                                                                                                                                                                      export type SIRARole =
                                                                                                                                                                                                                        | 'super_admin'
                                                                                                                                                                                                                          | 'org_admin'
                                                                                                                                                                                                                            | 'logistics_manager'
                                                                                                                                                                                                                              | 'fleet_manager'
                                                                                                                                                                                                                                | 'driver'
                                                                                                                                                                                                                                  | 'client_read'
                                                                                                                                                                                                                                    | 'analyst'
                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                    export const ROLE_HIERARCHY: Record<SIRARole, number> = {
                                                                                                                                                                                                                                      super_admin: 100,
                                                                                                                                                                                                                                        org_admin: 80,
                                                                                                                                                                                                                                          logistics_manager: 60,
                                                                                                                                                                                                                                            fleet_manager: 50,
                                                                                                                                                                                                                                              analyst: 40,
                                                                                                                                                                                                                                                driver: 20,
                                                                                                                                                                                                                                                  client_read: 10,
                                                                                                                                                                                                                                                  }
                                                                                                                                                                                                                                                  
                                                                                                                                                                                                                                                  export function hasMinimumRole(userRole: SIRARole, minimumRole: SIRARole): boolean {
                                                                                                                                                                                                                                                    return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[minimumRole]
                                                                                                                                                                                                                                                    }
                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                    export function canManageFleet(role: SIRARole): boolean {
                                                                                                                                                                                                                                                      return hasMinimumRole(role, 'fleet_manager')
                                                                                                                                                                                                                                                      }
                                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                      export function canViewAIInsights(role: SIRARole): boolean {
                                                                                                                                                                                                                                                        return hasMinimumRole(role, 'analyst')
                                                                                                                                                                                                                                                        }
                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                        export function canManageOrg(role: SIRARole): boolean {
                                                                                                                                                                                                                                                          return hasMinimumRole(role, 'org_admin')
                                                                                                                                                                                                                                                          }
