import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/database'

// Fallback values allow the module to load at build time without env vars.
// At runtime the real values from .env.local are always present.
export const supabase = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-key',
)
