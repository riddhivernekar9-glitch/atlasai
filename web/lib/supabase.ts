import { createBrowserClient } from '@supabase/ssr'

/**
 * Returns a Supabase client suitable for use in Client Components.
 * Call once per render; does not share state across server renders.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!,
  )
}
