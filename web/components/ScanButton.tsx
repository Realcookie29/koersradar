"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { requestScan } from "@/app/actions";

export function ScanButton({ busy }: { busy: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);
  const active = busy || pending;

  // Zolang er een scan loopt: elke 4 s verversen tot de worker klaar is.
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => router.refresh(), 4000);
    return () => clearInterval(t);
  }, [busy, router]);

  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <button
        onClick={() =>
          startTransition(async () => {
            const res = await requestScan();
            setMessage(res.ok ? (res.message ?? null) : `Mislukt: ${res.message}`);
            router.refresh();
          })
        }
        disabled={active}
        className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:brightness-110 disabled:cursor-wait disabled:opacity-70"
      >
        {active && <span className="size-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
        {active ? "Scan loopt…" : "Scan nu"}
      </button>
      {message && <span className="text-xs text-muted">{message}</span>}
    </div>
  );
}
