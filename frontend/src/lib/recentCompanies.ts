/** Company ids this browser opened last. Suggestions only: not a watchlist, never sent to the server. */
const RECENT_KEY = "citealpha.recent.companies";
const MAX_RECENT = 8;

export function readRecentCompanies(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(raw) ? raw.map(String).slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

export function rememberCompany(id: string): void {
  if (!id) return;
  try {
    const next = [id, ...readRecentCompanies().filter((item) => item !== id)].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable */
  }
}
