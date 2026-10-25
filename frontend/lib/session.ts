// The login token is kept in sessionStorage: it is cleared when the tab is closed,
// and the token itself expires after one hour. (See docs/AUTH.md for the trade-off.)
const KEY = "labreport_token";

export function saveToken(token: string): void {
  sessionStorage.setItem(KEY, token);
}

export function getToken(): string | null {
  return typeof window === "undefined" ? null : sessionStorage.getItem(KEY);
}

export function clearToken(): void {
  sessionStorage.removeItem(KEY);
}
