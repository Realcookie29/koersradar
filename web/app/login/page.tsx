"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Standaard invite-mails van Supabase leveren de sessie in de URL-hash
  // (#access_token=...&refresh_token=...). Die komt via de redirect hier terecht.
  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const access_token = hash.get("access_token");
    const refresh_token = hash.get("refresh_token");
    const hashError = hash.get("error_description");
    if (!hashError && (!access_token || !refresh_token)) return;

    async function consumeHash() {
      const { error } = hashError
        ? { error: { message: hashError } }
        : await createClient().auth.setSession({ access_token: access_token!, refresh_token: refresh_token! });
      window.history.replaceState(null, "", "/login");
      if (error) {
        setError(error.message);
        setState("error");
        return;
      }
      router.replace("/");
      router.refresh();
    }
    void consumeHash();
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setState("sending");
    const { error } = await createClient().auth.signInWithOtp({
      email,
      options: {
        // Alleen uitgenodigde vrienden: geen open registratie.
        shouldCreateUser: false,
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      setError(error.message);
      setState("error");
    } else {
      setState("sent");
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 p-6">
      <h1 className="text-2xl font-semibold">Koersradar</h1>
      {state === "sent" ? (
        <p>Check je mail voor de inloglink.</p>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <label className="text-sm" htmlFor="email">
            E-mailadres (alleen op uitnodiging)
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-neutral-400 bg-transparent px-3 py-2"
          />
          <button
            type="submit"
            disabled={state === "sending"}
            className="rounded bg-neutral-900 px-3 py-2 text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
          >
            {state === "sending" ? "Versturen…" : "Stuur inloglink"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>
      )}
    </main>
  );
}
