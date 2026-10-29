"use client";

import { useActionState, useState } from "react";
import { openTrade, type FormState } from "@/app/(portal)/journaal/actions";
import { fmtNum, fmtPrice } from "@/lib/format";
import { DEFAULT_COST_PCT, type Direction, pnlPerUnit, riskPerUnit, sizeForRisk, validate } from "@/lib/journal";

export type InstrumentOption = { id: number; symbol: string; currency: string; price: number | null };

export type Prefill = {
  instrumentId: number;
  direction: Direction;
  entry: number;
  stop: number;
  target: number | null;
  signalId: number;
};

const parse = (v: string): number | null => {
  if (v.trim() === "") return null;
  const n = Number(v.replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

const input =
  "num w-full rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm outline-none focus:border-text/40";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-muted">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-muted">{hint}</span>}
    </label>
  );
}

export function JournalForm({ instruments, prefill }: { instruments: InstrumentOption[]; prefill: Prefill | null }) {
  const [state, action, pending] = useActionState<FormState, FormData>(openTrade, null);
  const first = instruments.find((i) => i.id === prefill?.instrumentId) ?? instruments[0];
  const [instrumentId, setInstrumentId] = useState(first?.id ?? 0);
  const [direction, setDirection] = useState<Direction>(prefill?.direction ?? "long");
  const [entry, setEntry] = useState(String(prefill?.entry ?? first?.price ?? ""));
  const [stop, setStop] = useState(prefill ? String(prefill.stop) : "");
  const [target, setTarget] = useState(prefill?.target ? String(prefill.target) : "");
  const [account, setAccount] = useState("1000");
  const [riskPct, setRiskPct] = useState("1");
  const [manualQty, setManualQty] = useState("");

  const ins = instruments.find((i) => i.id === instrumentId);
  const e = parse(entry);
  const s = parse(stop);
  const t = parse(target);
  const problem = e !== null && s !== null ? validate(direction, e, s, t) : null;
  const levels = e !== null && s !== null && !problem ? { direction, entry: e, stop: s, costPct: DEFAULT_COST_PCT } : null;
  const riskAmount = (parse(account) ?? 0) * ((parse(riskPct) ?? 0) / 100);
  const qty = parse(manualQty) ?? (levels ? sizeForRisk(levels, riskAmount) : null);
  const loss = levels && qty ? riskPerUnit(levels) * qty : null;
  const gain = levels && qty && t !== null ? pnlPerUnit(levels, t) * qty : null;
  const costs = e !== null && qty ? e * qty * DEFAULT_COST_PCT * 2 : null;
  const cur = ins?.currency ?? "";

  const pickInstrument = (id: number) => {
    setInstrumentId(id);
    const price = instruments.find((i) => i.id === id)?.price;
    if (price) setEntry(String(price));
  };

  return (
    <form action={action} className="flex flex-col gap-4 rounded-2xl border border-line bg-panel p-5">
      <input type="hidden" name="instrument_id" value={instrumentId} />
      <input type="hidden" name="direction" value={direction} />
      <input type="hidden" name="quantity" value={qty ?? ""} />
      {prefill && <input type="hidden" name="signal_id" value={prefill.signalId} />}

      <div className="flex flex-wrap items-end gap-3">
        <Field label="Instrument">
          <select
            value={instrumentId}
            onChange={(ev) => pickInstrument(Number(ev.target.value))}
            className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm"
          >
            {instruments.map((i) => (
              <option key={i.id} value={i.id} className="bg-bg text-text">
                {i.symbol}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex rounded-full border border-line p-1 text-sm">
          {(["long", "short"] as const).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDirection(d)}
              className={`rounded-full px-3 py-1 ${direction === d ? "bg-accent text-on-accent" : "text-muted"}`}
            >
              {d === "long" ? "Long (koop)" : "Short"}
            </button>
          ))}
        </div>
        {ins?.price && <span className="num pb-2 text-xs text-muted">Laatste koers {fmtPrice(ins.price)}</span>}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Field label="Instap">
          <input name="entry_price" inputMode="decimal" value={entry} onChange={(ev) => setEntry(ev.target.value)} className={input} required />
        </Field>
        <Field label="Stop">
          <input name="stop_loss" inputMode="decimal" value={stop} onChange={(ev) => setStop(ev.target.value)} className={input} required />
        </Field>
        <Field label="Doel (optioneel)">
          <input name="target" inputMode="decimal" value={target} onChange={(ev) => setTarget(ev.target.value)} className={input} />
        </Field>
      </div>

      <fieldset className="grid grid-cols-1 gap-3 rounded-xl bg-panel-2/50 p-3 sm:grid-cols-3">
        <legend className="px-1 text-xs font-medium uppercase tracking-wide text-muted">Risicocalculator</legend>
        <Field label={`Rekening (${cur || "bedrag"})`} hint="Denkbeeldig bedrag">
          <input inputMode="decimal" value={account} onChange={(ev) => setAccount(ev.target.value)} className={input} />
        </Field>
        <Field label="Risico per trade (%)" hint="Gangbaar: 0,5 tot 1%">
          <input inputMode="decimal" value={riskPct} onChange={(ev) => setRiskPct(ev.target.value)} className={input} />
        </Field>
        <Field label="Aantal (optioneel)" hint="Leeg = berekend uit je risico">
          <input inputMode="decimal" value={manualQty} onChange={(ev) => setManualQty(ev.target.value)} className={input} />
        </Field>
      </fieldset>

      <dl className="num grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="font-sans text-xs text-muted">Aantal</dt>
          <dd>{qty ? fmtNum(qty, qty >= 100 ? 0 : 6) : "–"}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Positie</dt>
          <dd>{e !== null && qty ? `${fmtNum(e * qty)} ${cur}` : "–"}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Verlies bij stop</dt>
          <dd className="text-down">{loss !== null ? `−${fmtNum(loss)} ${cur}` : "–"}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Winst bij doel</dt>
          <dd className="text-up">{gain !== null ? `+${fmtNum(gain)} ${cur}` : "–"}</dd>
        </div>
      </dl>
      <p className="text-xs text-muted">
        Inclusief kosten van ongeveer {fmtNum(DEFAULT_COST_PCT * 100, 2)}% per kant
        {costs !== null && <> (samen ±{fmtNum(costs)} {cur})</>}
        {loss !== null && gain !== null && <>; verhouding winst/verlies na kosten {fmtNum(gain / loss)}</>}.
      </p>

      <Field label="Waarom deze trade? (optioneel)">
        <textarea name="reason" rows={2} maxLength={1000} className={`${input} font-sans`} placeholder="Bijv. breakout boven de high van gisteren" />
      </Field>

      <div className="flex flex-wrap items-center gap-3">
        <button
          disabled={pending || !!problem || !qty}
          className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-on-accent transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {pending ? "Opslaan…" : "Paper trade openen"}
        </button>
        {problem && <span className="text-sm text-warn">{problem}</span>}
        {state?.message && <span className={`text-sm ${state.ok ? "text-up" : "text-down"}`}>{state.message}</span>}
      </div>
    </form>
  );
}
