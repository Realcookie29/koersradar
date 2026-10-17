"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

// "Scan nu": zet een aanvraag klaar; de worker pakt hem binnen ~20 s op.
// RLS staat alleen trigger='manual' op eigen naam toe.
export async function requestScan(): Promise<{ ok: boolean; message?: string }> {
  const supabase = await createClient();
  const { data: pending } = await supabase
    .from("scan_runs")
    .select("id")
    .in("status", ["pending", "running"])
    .limit(1);
  if (pending?.length) return { ok: true, message: "Er loopt al een scan." };

  const { error } = await supabase.from("scan_runs").insert({ trigger: "manual" });
  if (error) return { ok: false, message: error.message };
  revalidatePath("/");
  return { ok: true };
}
