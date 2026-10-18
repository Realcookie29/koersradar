"use server";

import { revalidatePath } from "next/cache";
import { DEFAULT_COST_PCT, type Direction, validate } from "@/lib/journal";
import { createClient } from "@/lib/supabase/server";

export type FormState = { ok: boolean; message?: string } | null;

const num = (v: FormDataEntryValue | null): number | null => {
  if (typeof v !== "string" || v.trim() === "") return null;
  const n = Number(v.replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

const text = (v: FormDataEntryValue | null, max = 1000): string | null => {
  if (typeof v !== "string") return null;
  const t = v.trim().slice(0, max);
  return t || null;
};

// RLS zorgt dat je alleen trades op eigen naam kunt toevoegen, wijzigen of verwijderen.
export async function openTrade(_: FormState, form: FormData): Promise<FormState> {
  const direction: Direction = form.get("direction") === "short" ? "short" : "long";
  const instrumentId = num(form.get("instrument_id"));
  const entry = num(form.get("entry_price"));
  const stop = num(form.get("stop_loss"));
  const target = num(form.get("target"));
  const quantity = num(form.get("quantity"));
  const signalId = num(form.get("signal_id"));

  if (!instrumentId) return { ok: false, message: "Kies een instrument." };
  const problem = validate(direction, entry ?? 0, stop ?? 0, target);
  if (problem) return { ok: false, message: problem };
  if (!quantity || quantity <= 0) return { ok: false, message: "Vul een rekeninggrootte en risico in, of een aantal." };

  const supabase = await createClient();
  const { error } = await supabase.from("journal_trades").insert({
    instrument_id: instrumentId,
    signal_id: signalId,
    direction,
    entry_price: entry,
    stop_loss: stop,
    target,
    quantity,
    cost_pct: DEFAULT_COST_PCT,
    reason: text(form.get("reason")),
  });
  if (error) return { ok: false, message: error.message };
  revalidatePath("/journaal");
  return { ok: true, message: "Paper trade vastgelegd." };
}

export async function closeTrade(_: FormState, form: FormData): Promise<FormState> {
  const id = num(form.get("id"));
  const exit = num(form.get("exit_price"));
  if (!id) return { ok: false, message: "Onbekende trade." };
  if (!exit || exit <= 0) return { ok: false, message: "Vul een geldige uitstapkoers in." };

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("journal_trades")
    .update({ exit_price: exit, closed_at: new Date().toISOString(), exit_note: text(form.get("exit_note")) })
    .eq("id", id)
    .is("closed_at", null)
    .select("id");
  if (error) return { ok: false, message: error.message };
  if (!data?.length) return { ok: false, message: "Deze trade is al gesloten of niet van jou." };
  revalidatePath("/journaal");
  return { ok: true };
}

export async function deleteTrade(id: number): Promise<FormState> {
  const supabase = await createClient();
  const { data, error } = await supabase.from("journal_trades").delete().eq("id", id).select("id");
  if (error) return { ok: false, message: error.message };
  if (!data?.length) return { ok: false, message: "Deze trade is niet van jou." };
  revalidatePath("/journaal");
  return { ok: true };
}
