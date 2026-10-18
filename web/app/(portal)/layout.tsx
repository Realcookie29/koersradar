import { connection } from "next/server";
import { Suspense } from "react";
import { TopNav } from "@/components/TopNav";
import { createClient } from "@/lib/supabase/server";

async function TopNavWithUser() {
  await connection(); // Supabase-auth gebruikt de klok
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  return <TopNav email={(data?.claims?.email as string | undefined) ?? null} />;
}

// Statische plek-houder (geen hooks): de echte menubalk gebruikt usePathname().
function TopNavSkeleton() {
  return <div className="h-[60px] xl:h-[68px]" />;
}

export default function PortalLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex min-h-screen flex-col">
      <Suspense fallback={<TopNavSkeleton />}>
        <TopNavWithUser />
      </Suspense>
      <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:py-12">{children}</main>
      <footer className="px-4 pb-6 text-center text-xs text-muted sm:px-8">
        Beslisondersteuning, geen advies. Geen trade is ook een uitkomst.
      </footer>
    </div>
  );
}
