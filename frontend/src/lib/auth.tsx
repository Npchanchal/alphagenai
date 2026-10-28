import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  fetchAuthMe,
  postGuest,
  postLogin,
  postLogout,
  postRegister,
  putPreferences,
  type AuthUser,
  type UserPreferences,
} from "../lib/api";
import { useI18n } from "../i18n";
import type { LangCode } from "../i18n/languages";

const TOKEN_KEY = "intellens.auth.token";
const LOCAL_PREFS_KEY = "intellens.prefs";

type AuthCtx = {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string, totpCode?: string) => Promise<AuthUser>;
  register: (
    email: string,
    password: string,
    name: string,
    opts?: {
      acceptTerms?: boolean;
      accountType?: "retail" | "b2b";
      orgName?: string;
      challengeId?: string;
      challengeAnswer?: string;
    },
  ) => Promise<void>;
  continueAsGuest: (
    acceptTerms?: boolean,
    challenge?: { challengeId: string; challengeAnswer: string },
  ) => Promise<void>;
  adoptToken: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  updatePreferences: (patch: Partial<UserPreferences>) => Promise<void>;
  preferences: UserPreferences | null;
};

const Ctx = createContext<AuthCtx | null>(null);

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

function readLocalPrefs(): Partial<UserPreferences> {
  try {
    const raw = localStorage.getItem(LOCAL_PREFS_KEY);
    return raw ? (JSON.parse(raw) as Partial<UserPreferences>) : {};
  } catch {
    return {};
  }
}

function writeLocalPrefs(prefs: UserPreferences) {
  try {
    localStorage.setItem(LOCAL_PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { lang, setLang } = useI18n();
  const [token, setToken] = useState<string | null>(readToken);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);

  const applySession = useCallback(
    (nextToken: string, nextUser: AuthUser) => {
      writeToken(nextToken);
      setToken(nextToken);
      setUser(nextUser);
      setPreferences(nextUser.preferences);
      writeLocalPrefs(nextUser.preferences);
      if (nextUser.preferences.language && nextUser.preferences.language !== lang) {
        setLang(nextUser.preferences.language as LangCode);
      }
    },
    [lang, setLang],
  );

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      const tkn = readToken();
      if (!tkn) {
        const local = readLocalPrefs();
        if (local.language) setLang(local.language as LangCode);
        if (Object.keys(local).length) {
          setPreferences({
            language: "en",
            default_market: "IN",
            default_index: "SENSEX",
            watchlist: [],
            show_demo_tape: true,
            density: "compact",
            ...local,
          } as UserPreferences);
        }
        setLoading(false);
        return;
      }
      try {
        let me: { user: AuthUser } | null = null;
        let denied = false;
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            me = await fetchAuthMe(tkn);
            break;
          } catch (e) {
            const status = e instanceof ApiError ? e.status : 0;
            if (status === 401 || status === 403) {
              denied = true;
              break;
            }
            if (status === 429 && attempt < 2) {
              await new Promise((resolve) => window.setTimeout(resolve, 1500 * (attempt + 1)));
              continue;
            }
            break;
          }
        }
        if (cancelled) return;
        if (me) {
          applySession(tkn, me.user);
        } else if (denied) {
          writeToken(null);
          setToken(null);
          setUser(null);
        } else {
          // A rate limit or a network blip is not a logout. Keep the stored session.
          setToken(tkn);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email: string, password: string, totpCode?: string) => {
      const res = await postLogin(email, password, totpCode);
      applySession(res.token, res.user);
      return res.user;
    },
    [applySession],
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      name: string,
      opts?: {
        acceptTerms?: boolean;
        accountType?: "retail" | "b2b";
        orgName?: string;
        challengeId?: string;
        challengeAnswer?: string;
      },
    ) => {
      const res = await postRegister({
        email,
        password,
        name,
        accept_terms: opts?.acceptTerms ?? true,
        account_type: opts?.accountType ?? "b2b",
        org_name: opts?.orgName,
        guest_token: user?.kind === "guest" ? token ?? undefined : undefined,
        challenge_id: opts?.challengeId,
        challenge_answer: opts?.challengeAnswer,
        preferences: {
          language: lang,
          ...readLocalPrefs(),
        },
      });
      applySession(res.token, res.user);
      const { trackEvent } = await import("./analytics");
      trackEvent("register");
    },
    [applySession, lang, token, user],
  );

  const continueAsGuest = useCallback(
    async (
      acceptTerms = true,
      challenge?: { challengeId: string; challengeAnswer: string },
    ) => {
      const res = await postGuest({
        accept_terms: acceptTerms,
        challenge_id: challenge?.challengeId,
        challenge_answer: challenge?.challengeAnswer,
      });
      const merged = {
        ...res.user.preferences,
        ...readLocalPrefs(),
        language: lang,
      } as UserPreferences;
      applySession(res.token, { ...res.user, preferences: merged });
      const prefs = await putPreferences(res.token, merged);
      setPreferences(prefs.preferences);
      writeLocalPrefs(prefs.preferences);
      const { trackEvent } = await import("./analytics");
      trackEvent("guest_continue");
    },
    [applySession, lang],
  );

  const adoptToken = useCallback(
    async (nextToken: string) => {
      const me = await fetchAuthMe(nextToken);
      applySession(nextToken, me.user);
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    if (token) {
      try {
        await postLogout(token);
      } catch {
        /* ignore */
      }
    }
    writeToken(null);
    setToken(null);
    setUser(null);
    setPreferences(null);
  }, [token]);

  const updatePreferences = useCallback(
    async (patch: Partial<UserPreferences>) => {
      if (patch.language) setLang(patch.language as LangCode);
      if (token) {
        const res = await putPreferences(token, patch);
        setPreferences(res.preferences);
        writeLocalPrefs(res.preferences);
        if (user) setUser({ ...user, preferences: res.preferences });
      } else {
        const next = { ...(preferences ?? readLocalPrefs()), ...patch } as UserPreferences;
        setPreferences(next);
        writeLocalPrefs(next);
      }
    },
    [preferences, setLang, token, user],
  );

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      login,
      register,
      continueAsGuest,
      adoptToken,
      logout,
      updatePreferences,
      preferences,
    }),
    [
      user,
      token,
      loading,
      login,
      register,
      continueAsGuest,
      adoptToken,
      logout,
      updatePreferences,
      preferences,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth requires AuthProvider");
  return ctx;
}
