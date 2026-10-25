"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError, User } from "@/lib/api";
import { clearToken, getToken } from "@/lib/session";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    api
      .me(token)
      .then(setUser)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          router.replace("/login");
        } else {
          setError(err instanceof ApiError ? err.message : "Something went wrong.");
        }
      });
  }, [router]);

  async function logout() {
    const token = getToken();
    if (token) await api.logout(token).catch(() => undefined);
    clearToken();
    router.replace("/login");
  }

  return (
    <main>
      <h1>Dashboard</h1>
      {error && <div className="message error" role="alert">{error}</div>}
      {!user && !error && <p>Loading...</p>}
      {user && (
        <div className="card">
          <h2>Your account</h2>
          <dl>
            <dt>Email</dt>
            <dd>{user.email}</dd>
            <dt>Role</dt>
            <dd>{user.role}</dd>
          </dl>
          <p className="lead">Uploading and analysing reports is added in the next weeks.</p>
          <button onClick={logout}>Log out</button>
        </div>
      )}
    </main>
  );
}
