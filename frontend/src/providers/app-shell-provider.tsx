"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { Locale, TranslationKey, translations } from "@/lib/i18n/translations";

type Theme = "light" | "dark";

interface AppShellContextValue {
  locale: Locale;
  theme: Theme;
  user: Record<string, unknown> | null;
  setLocale: (locale: Locale) => void;
  setTheme: (theme: Theme) => void;
  setAuth: (payload: Record<string, unknown> | null) => void;
  t: (key: TranslationKey) => string;
}

const AppShellContext = createContext<AppShellContextValue | null>(null);

export function AppShellProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("pt");
  const [theme, setThemeState] = useState<Theme>("dark");
  const [user, setUser] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const storedLocale = window.localStorage.getItem("aml-locale") as Locale | null;
    const storedTheme = window.localStorage.getItem("aml-theme") as Theme | null;
    const storedAuth = window.localStorage.getItem("aml-auth");
    if (storedLocale) setLocaleState(storedLocale);
    if (storedTheme) setThemeState(storedTheme);
    if (storedAuth) {
      try {
        const parsed = JSON.parse(storedAuth);
        setUser(parsed.user ?? null);
      } catch {
        window.localStorage.removeItem("aml-auth");
      }
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("aml-theme", theme);
  }, [theme]);

  const setLocale = (nextLocale: Locale) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem("aml-locale", nextLocale);
  };

  const setTheme = (nextTheme: Theme) => {
    setThemeState(nextTheme);
  };

  const setAuth = (payload: Record<string, unknown> | null) => {
    setUser(payload?.user as Record<string, unknown> | null);
    if (payload) {
      window.localStorage.setItem("aml-auth", JSON.stringify(payload));
    } else {
      window.localStorage.removeItem("aml-auth");
    }
  };

  const value = useMemo<AppShellContextValue>(
    () => ({
      locale,
      theme,
      user,
      setLocale,
      setTheme,
      setAuth,
      t: (key) => translations[locale][key] ?? key
    }),
    [locale, theme, user]
  );

  return <AppShellContext.Provider value={value}>{children}</AppShellContext.Provider>;
}

export function useAppShell() {
  const context = useContext(AppShellContext);
  if (!context) throw new Error("useAppShell must be used within AppShellProvider");
  return context;
}
