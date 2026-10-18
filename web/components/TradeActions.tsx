"use client";

import { useActionState, useState, useTransition } from "react";
import { closeTrade, deleteTrade, type FormState } from "@/app/(portal)/journaal/actions";

/** Sluiten (tegen de laatste koers of een eigen koers) en verwijderen van een eigen paper trade. */
export function TradeActions({ id, price, open }: { id: number; price: number | null; open: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(closeTrade, null);
  const [deleting, startDelete] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [showClose, setShowClose] = useState(false);

  const remove = () => {
    if (!window.confirm("Deze trade verwijderen? Dat kan niet ongedaan worden.")) return;
    startDelete(async () => {
      const res = await deleteTrade(id);
      if (res && !res.ok) setError(res.message ?? "Verwijderen mislukt.");
    });
  };

  return (
    <div className="flex flex-col items-end gap-2 text-xs">
      <div className="flex gap-2">
        {open && (
          <button type="button" onClick={() => setShowClose((v) => !v)} className="rounded-full border border-line px-3 py-1 hover:bg-panel-2">
            Sluiten
          </button>
        )}
        <button type="button" onClick={remove} disabled={deleting} className="rounded-full px-2 py-1 text-muted hover:text-down disabled:opacity-40">
          Verwijderen
        </button>
      </div>
      {open && showClose && (
        <form action={action} className="flex flex-wrap items-center justify-end gap-2">
          <input type="hidden" name="id" value={id} />
          <input
            name="exit_price"
            inputMode="decimal"
            defaultValue={price ?? ""}
            aria-label="Uitstapkoers"
            className="num w-28 rounded-lg border border-line bg-panel-2 px-2 py-1"
          />
          <input name="exit_note" maxLength={1000} placeholder="Notitie" aria-label="Notitie" className="w-32 rounded-lg border border-line bg-panel-2 px-2 py-1" />
          <button disabled={pending} className="rounded-full bg-accent px-3 py-1 font-medium text-on-accent disabled:opacity-40">
            {pending ? "…" : "Bevestig"}
          </button>
        </form>
      )}
      {(state?.message && !state.ok) || error ? <span className="text-down">{error ?? state?.message}</span> : null}
    </div>
  );
}
