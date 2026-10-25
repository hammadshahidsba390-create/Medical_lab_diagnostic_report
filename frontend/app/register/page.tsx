"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.register(email, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <div className="card" style={{ maxWidth: 420, margin: "0 auto" }}>
        <h1>Create an account</h1>
        {done ? (
          <div className="message" role="status">
            Account created. <Link href="/login">Log in</Link> to continue.
          </div>
        ) : (
          <form onSubmit={onSubmit}>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            <label htmlFor="password">Password (8 to 72 characters)</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <div className="message error" role="alert">{error}</div>}
            <button className="primary" type="submit" disabled={busy}>{busy ? "Creating..." : "Create account"}</button>
          </form>
        )}
        <p>Already registered? <Link href="/login">Log in</Link>.</p>
      </div>
    </main>
  );
}
