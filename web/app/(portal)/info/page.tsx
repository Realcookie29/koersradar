import Link from "next/link";
import { STEPS } from "@/components/signals";

const NOW = [
  {
    title: "Scanner",
    href: "/",
    text: "Haalt elke 15 minuten verse koersen op en zoekt naar koopkansen. Bij een kans zie je instap, stop, doel en de verhouding tussen winst en risico. Geen kans is ook een uitkomst: liever niet traden dan een zwak signaal volgen.",
  },
  {
    title: "Markten",
    href: "/markten",
    text: "Per instrument hoe vers de data is: welke bron, wanneer de laatste candle was en of er iets ontbreekt.",
  },
  {
    title: "Grafiek",
    href: "/markten",
    text: "Candles met EMA 50, EMA 200, RSI en volume. Bij een actieve kans staan instap, stop en doel als lijnen in de grafiek.",
  },
  {
    title: "Signalenlog",
    href: "/signalen",
    text: "Alle koopsignalen die de scanner gaf, zodat we achteraf kunnen zien wat werkte.",
  },
  {
    title: "Backtest",
    href: "/backtest",
    text: "Hoe de regels van de scanner het sinds 2021 hadden gedaan, na kosten, vergeleken met kopen en vasthouden en met willekeurig instappen.",
  },
  {
    title: "AI-uitleg",
    text: "Bij een kans schrijft Claude een korte uitleg in gewone taal. De AI rekent zelf niets: een uitleg met een getal dat niet uit de berekening komt, wordt afgewezen.",
  },
];

const NEXT = [
  {
    title: "Watchlist",
    text: "Iedereen een eigen lijst met instrumenten die hij of zij wil volgen.",
  },
  {
    title: "Paper trading",
    text: "Signalen automatisch met nepgeld uitvoeren, met vaste grenzen: maximaal 1% risico per trade en maximaal 3% verlies per dag. Elke trade blijft gekoppeld aan zijn signaal.",
  },
  {
    title: "Evaluatie",
    text: "Na minstens vier weken paper trading samen bekijken wat werkte, en pas dan besluiten over nieuwe methoden of betere AEX-data.",
  },
];

const KNOW = [
  "Koersradar is beslisondersteuning, geen beleggingsadvies. Signalen zijn geen zekerheden en beloven geen winst.",
  "Er worden geen echte orders geplaatst. De code bevat bewust geen sleutels waarmee je kunt handelen.",
  "De huidige strategie verliest in de backtest gemiddeld geld na kosten. Volg de signalen nog niet met echt geld.",
  "AEX-koersen komen uit een onofficiële bron en zijn experimenteel. Ze kunnen vertraagd of onvolledig zijn.",
  "De koersdata is alleen bedoeld voor deze besloten groep. Daarom kun je je alleen op uitnodiging aanmelden.",
];

function Card({ title, text, href }: { title: string; text: string; href?: string }) {
  const body = (
    <>
      <h3 className="font-medium">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-muted">{text}</p>
    </>
  );
  return href ? (
    <Link href={href} className="rounded-2xl border border-line bg-panel p-4 transition-colors hover:bg-panel-2">
      {body}
    </Link>
  ) : (
    <div className="rounded-2xl border border-line bg-panel p-4">{body}</div>
  );
}

export default function InfoPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-10">
        <h1 className="animate-fade-slide-in-1 font-display text-4xl tracking-tight sm:text-5xl">Over Koersradar</h1>
        <p className="animate-fade-slide-in-2 mt-3 max-w-2xl leading-relaxed text-muted">
          Een gedeeld platform voor een kleine vriendengroep om crypto en AEX-aandelen te analyseren voor daytrading. Het
          doel is eerlijk en veilig testen of een strategie werkt, voordat er echt geld in gaat.
        </p>
      </header>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Wat het nu doet</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {NOW.map((c) => (
            <Card key={c.title} {...c} />
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="mb-1 text-sm font-medium uppercase tracking-wide text-muted">Hoe de scanner beslist</h2>
        <p className="mb-4 max-w-2xl text-sm text-muted">
          De strategie heet trend-pullback: kopen als de koers in een stijgende trend even terugzakt en weer omhoog draait.
          Een instrument moet alle stappen halen, anders is de uitkomst &quot;geen trade&quot;.
        </p>
        <ol className="grid gap-2 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step} className="flex items-center gap-3 rounded-2xl border border-line bg-panel px-4 py-3 text-sm">
              <span className="num grid size-7 shrink-0 place-items-center rounded-full bg-panel-2 text-xs">{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
        <p className="mt-3 max-w-2xl text-sm text-muted">
          De stop ligt op 1,5 keer de gemiddelde beweging per candle (ATR) onder de instap, het doel op twee keer die
          afstand erboven. Kosten zoals fees, spread en slippage worden meegerekend.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Wat er nog komt</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {NEXT.map((c) => (
            <Card key={c.title} {...c} />
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Goed om te weten</h2>
        <ul className="space-y-2 rounded-2xl border border-line bg-panel p-5 text-sm leading-relaxed">
          {KNOW.map((k) => (
            <li key={k} className="flex gap-3">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-warn" />
              {k}
            </li>
          ))}
        </ul>
      </section>

      <section className="text-sm text-muted">
        <h2 className="mb-2 text-sm font-medium uppercase tracking-wide">Achter de schermen</h2>
        <p className="max-w-2xl leading-relaxed">
          De berekeningen gebeuren in Python-code met tests, de website is gebouwd met Next.js en de data en accounts staan
          in Supabase. Crypto-koersen komen van Binance, met Coinbase als reserve. De grafieken gebruiken TradingView
          Lightweight Charts.
        </p>
      </section>
    </div>
  );
}
