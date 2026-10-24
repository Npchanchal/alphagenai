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
  DEFAULT_LANG,
  LANG_STORAGE_KEY,
  LANGUAGES,
  type LangCode,
} from "./languages";

import en from "./locales/en.json";

type Dict = Record<string, string>;
type LocaleModule = { default: Dict };

const EN = en as Dict;
const cache = new Map<LangCode, Dict>([["en", EN]]);
const inflight = new Map<LangCode, Promise<Dict>>();

function loadLocale(code: LangCode): Promise<Dict> {
  const held = cache.get(code);
  if (held) return Promise.resolve(held);
  const pending = inflight.get(code);
  if (pending) return pending;
  const request = import(`./locales/${code}.json`).then((mod: LocaleModule) => {
    const dict = mod.default;
    cache.set(code, dict);
    inflight.delete(code);
    return dict;
  });
  inflight.set(code, request);
  return request;
}

type I18nCtx = {
  lang: LangCode;
  setLang: (code: LangCode) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  dir: "ltr" | "rtl";
};

const Ctx = createContext<I18nCtx | null>(null);

function resolveInitial(): LangCode {
  try {
    const stored = localStorage.getItem(LANG_STORAGE_KEY) as LangCode | null;
    if (stored && LANGUAGES.some((l) => l.code === stored)) return stored;
  } catch {
    /* ignore */
  }
  return DEFAULT_LANG;
}

function applyDocumentLang(code: LangCode) {
  const meta = LANGUAGES.find((l) => l.code === code);
  document.documentElement.lang = code;
  document.documentElement.dir = meta?.dir === "rtl" ? "rtl" : "ltr";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LangCode>(resolveInitial);
  const [dict, setDict] = useState<Dict>(() => cache.get(resolveInitial()) ?? EN);

  useEffect(() => {
    applyDocumentLang(lang);
    try {
      localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch {
      /* ignore */
    }
    let cancelled = false;
    void loadLocale(lang).then((next) => {
      if (!cancelled) setDict(next);
    });
    return () => {
      cancelled = true;
    };
  }, [lang]);

  const setLang = useCallback((code: LangCode) => {
    setLangState(code);
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      let text = dict[key] ?? EN[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          text = text.split(`{${k}}`).join(String(v));
        }
      }
      return text;
    },
    [dict],
  );

  const dir: "ltr" | "rtl" =
    LANGUAGES.find((l) => l.code === lang)?.dir === "rtl" ? "rtl" : "ltr";

  const value = useMemo(() => ({ lang, setLang, t, dir }), [lang, setLang, t, dir]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18nCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n requires I18nProvider");
  return ctx;
}
