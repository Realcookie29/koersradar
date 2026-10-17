"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Scanner", icon: "M3 12h4l3-8 4 16 3-8h4" },
  { href: "/markten", label: "Markten", icon: "M4 19V5m0 14h16M8 15l3-4 3 2 5-6" },
  { href: "/signalen", label: "Signalenlog", icon: "M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" },
];

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="size-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={d} />
    </svg>
  );
}

export function Sidebar({ email }: { email: string | null }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const active = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          onClick={() => setOpen(false)}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
            active(item.href) ? "bg-panel-2 text-text" : "text-muted hover:bg-panel-2/60 hover:text-text"
          }`}
        >
          <Icon d={item.icon} />
          {item.label}
        </Link>
      ))}
    </nav>
  );

  return (
    <>
      {/* Mobiele balk */}
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-panel px-4 py-3 md:hidden">
        <Logo />
        <button onClick={() => setOpen(!open)} className="rounded-md border border-line px-3 py-1 text-sm" aria-expanded={open}>
          Menu
        </button>
      </div>
      {open && <div className="border-b border-line bg-panel p-3 md:hidden">{nav}</div>}

      {/* Desktop zijbalk */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col justify-between border-r border-line bg-panel p-4 md:flex">
        <div className="flex flex-col gap-6">
          <Logo />
          {nav}
        </div>
        <div className="flex flex-col gap-3 border-t border-line pt-4 text-xs text-muted">
          <p className="leading-relaxed">Beslisondersteuning, geen advies. Geen trade is ook een uitkomst.</p>
          {email && <p className="truncate" title={email}>{email}</p>}
          <form action="/auth/signout" method="post">
            <button className="text-muted underline-offset-2 hover:text-text hover:underline">Uitloggen</button>
          </form>
        </div>
      </aside>
    </>
  );
}

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="grid size-7 place-items-center rounded-md bg-accent/15 text-accent">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
          <circle cx="12" cy="12" r="8" />
          <path d="M12 12l5-5" strokeLinecap="round" />
        </svg>
      </span>
      Koersradar
    </Link>
  );
}
