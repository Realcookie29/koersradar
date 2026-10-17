import { createBrowserClient } from "@supabase/ssr";

// Browser-client: alleen de publieke anon key. Toegang wordt afgedwongen door RLS.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
