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

export type ExtractedRow = {
  raw_name: string;
  value: number | string;
  unit?: string | null;
  reference_range?: string | null;
};

export type ResultRow = {
  raw_name: string;
  biomarker_id: string | null;
  biomarker_name: string | null;
  match_score: number;
  value: number | string;
  unit?: string | null;
  reference_range?: string | null;
  range_source: "report" | "unavailable";
  flag: "low" | "normal" | "high" | "unknown";
};

export type ReportSummary = {
  total: number;
  low: number;
  normal: number;
  high: number;
  unknown: number;
  unmatched: number;
};

export type Report = {
  id: string;
  user_id: string;
  title: string;
  results: ResultRow[];
  summary: ReportSummary;
  created_at: string;
  disclaimer: string;
};

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
  createReport: (token: string, title: string, rows: ExtractedRow[]) =>
    request<Report>("/api/v1/reports", { method: "POST", body: JSON.stringify({ title, rows }) }, token),
  listReports: (token: string) => request<Report[]>("/api/v1/reports", {}, token),
  getReport: (token: string, id: string) => request<Report>(`/api/v1/reports/${id}`, {}, token),
  deleteReport: (token: string, id: string) => request<void>(`/api/v1/reports/${id}`, { method: "DELETE" }, token),
};
