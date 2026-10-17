import { connection } from "next/server";
import { Suspense } from "react";
import { Sidebar } from "@/components/Sidebar";
import { createClient } from "@/lib/supabase/server";

async function SidebarWithUser() {
  await connection(); // Supabase-auth gebruikt de klok
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  return <Sidebar email={(data?.claims?.email as string | undefined) ?? null} />;
}

// Statische plek-houder (geen hooks): de echte zijbalk gebruikt usePathname().
function SidebarSkeleton() {
  return <aside className="hidden h-screen w-60 shrink-0 border-r border-line bg-panel md:block" />;
}

export default function PortalLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Suspense fallback={<SidebarSkeleton />}>
        <SidebarWithUser />
      </Suspense>
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8">{children}</main>
    </div>
  );
}
