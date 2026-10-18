"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Scanner" },
  { href: "/markten", label: "Markten" },
  { href: "/signalen", label: "Signalenlog" },
  { href: "/journaal", label: "Journaal" },
  { href: "/backtest", label: "Backtest" },
];

export function TopNav({ email }: { email: string | null }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const active = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  const signout = (
    <form action="/auth/signout" method="post">
      <button className="ml-1 inline-flex items-center gap-2 rounded-full bg-accent px-3.5 py-2 text-sm font-medium text-on-accent transition-opacity hover:opacity-90">
        Uitloggen
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M7 7h10v10" />
          <path d="M7 17 17 7" />
        </svg>
      </button>
    </form>
  );

  return (
    <header className="relative z-30 px-4 pt-4 sm:px-6 xl:pt-6">
      <div className="flex items-center justify-between gap-4">
        <Logo />

        <div className="hidden items-center gap-3 md:flex">
          {email && (
            <span className="hidden max-w-56 truncate text-sm text-muted lg:inline" title={email}>
              {email}
            </span>
          )}
          <nav className="flex items-center gap-1 rounded-full bg-panel px-1 py-1 ring-1 ring-line backdrop-blur">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-3 py-2 text-sm font-medium transition-colors hover:text-text ${
                  active(item.href) ? "bg-panel-2 text-text" : "text-muted"
                }`}
              >
                {item.label}
              </Link>
            ))}
            {signout}
          </nav>
          <InfoButton active={active("/info")} />
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <InfoButton active={active("/info")} />
          <button
            onClick={() => setOpen(!open)}
            className="inline-flex size-10 items-center justify-center rounded-full bg-panel-2 ring-1 ring-line backdrop-blur"
            aria-expanded={open}
            aria-label="Menu openen of sluiten"
          >
          <svg viewBox="0 0 24 24" className="size-5 text-text" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
            <path d="M4 5h16" />
            <path d="M4 12h16" />
            <path d="M4 19h16" />
          </svg>
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-3 flex flex-col gap-1 rounded-2xl bg-panel p-2 ring-1 ring-line backdrop-blur md:hidden">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className={`rounded-full px-4 py-2.5 text-sm font-medium ${active(item.href) ? "bg-panel-2 text-text" : "text-muted"}`}
            >
              {item.label}
            </Link>
          ))}
          <div className="flex items-center justify-between gap-3 px-2 pt-2">
            {email && <span className="truncate text-xs text-muted">{email}</span>}
            {signout}
          </div>
        </div>
      )}
    </header>
  );
}

function InfoButton({ active }: { active: boolean }) {
  return (
    <Link
      href="/info"
      title="Over Koersradar"
      aria-label="Over Koersradar"
      className={`grid size-10 place-items-center rounded-full ring-1 ring-line backdrop-blur transition-colors hover:text-text ${
        active ? "bg-panel-2 text-text" : "bg-panel text-muted"
      }`}
    >
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5" />
        <path d="M12 8h.01" />
      </svg>
    </Link>
  );
}

function Logo() {
  return (
    <Link href="/" className="flex items-center">
      {/* Wit script-logo uit Stitch; in de lichte variant omgekeerd naar donker */}
      <Image
        src="/logo-koersradar.png"
        alt="Koersradar"
        width={820}
        height={251}
        priority
        className="h-11 w-auto invert dark:invert-0"
      />
    </Link>
  );
}
