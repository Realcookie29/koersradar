import Link from "next/link";

export const MARKETS = [
  { key: "alles", label: "Alles" },
  { key: "crypto", label: "Crypto" },
  { key: "aex", label: "Aandelen" },
] as const;
export type MarketKey = (typeof MARKETS)[number]["key"];

/** Leest ?markt= uit de URL; onbekend of leeg geeft `fallback`. */
export function marketFrom<K extends MarketKey>(value: unknown, allowed: readonly K[], fallback: K): K {
  return allowed.includes(value as K) ? (value as K) : fallback;
}

/** Knoppen om tussen markten te wisselen. De standaardkeuze krijgt de kale URL. */
export function MarketToggle({
  path,
  active,
  options,
  fallback,
}: {
  path: string;
  active: MarketKey;
  options: readonly MarketKey[];
  fallback: MarketKey;
}) {
  return (
    <nav className="flex gap-1 rounded-full border border-line bg-panel p-1">
      {MARKETS.filter((m) => options.includes(m.key)).map((m) => (
        <Link
          key={m.key}
          href={m.key === fallback ? path : `${path}?markt=${m.key}`}
          className={`rounded-full px-3.5 py-1 text-sm font-medium ${m.key === active ? "bg-panel-2 text-text" : "text-muted hover:text-text"}`}
        >
          {m.label}
        </Link>
      ))}
    </nav>
  );
}
