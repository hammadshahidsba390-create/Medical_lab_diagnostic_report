const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 15000;

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export type User = { id: string; email: string; role: string };
export type TokenResponse = { access_token: string; token_type: string; expires_in: number };

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    const response = await fetch(`${BASE_URL}${path}`, { ...options, headers, signal: controller.signal });
    if (response.status === 204) return undefined as T;
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const error = body?.error;
      throw new ApiError(response.status, error?.code ?? "unknown_error", error?.message ?? "Something went wrong.");
    }
    return body as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, "network_error", "The server could not be reached. Please try again.");
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: (token: string) => request<void>("/api/v1/auth/logout", { method: "POST" }, token),
  me: (token: string) => request<User>("/api/v1/me", {}, token),
};
