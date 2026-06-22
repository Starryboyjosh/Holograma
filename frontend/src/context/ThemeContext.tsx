import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { apiFetch } from '../lib/backend';

export type AppearanceTheme = 'light' | 'dark' | 'system';

interface ThemeValue {
  /** Persisted preference: explicit light/dark or time-of-day 'system'. */
  appearance: AppearanceTheme;
  setAppearance: (t: AppearanceTheme) => void;
  /** Resolved boolean actually applied to the document. */
  isDark: boolean;
  /** Convenience toggle for the header button (flips to explicit light/dark). */
  toggle: () => void;
}

const ThemeCtx = createContext<ThemeValue | null>(null);

function resolveDark(appearance: AppearanceTheme): boolean {
  if (appearance === 'dark') return true;
  if (appearance === 'light') return false;
  const hour = new Date().getHours();
  return hour < 7 || hour > 18;
}

const STORAGE_KEY = 'holograma-appearance';

function initialAppearance(): AppearanceTheme {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  return 'dark'; // UNEV default: dark premium.
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [appearance, setAppearanceState] = useState<AppearanceTheme>(initialAppearance);

  // Apply the `.dark` class to <html> whenever the resolved theme changes.
  const isDark = resolveDark(appearance);
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', isDark);
  }, [isDark]);

  // Seed once from the backend (HOLOGRAM_MODE), like the original App did, so the
  // kiosk picks up the configured theme. localStorage wins for instant paint; the
  // backend value only applies if the user never set a local preference.
  useEffect(() => {
    let active = true;
    if (localStorage.getItem(STORAGE_KEY)) return;
    void apiFetch('/api/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!active || !data?.HOLOGRAM_MODE) return;
        const mode = data.HOLOGRAM_MODE;
        if (mode === 'light' || mode === 'dark' || mode === 'system') {
          setAppearanceState(mode);
        }
      })
      .catch(() => {
        /* offline / web mode without backend — keep the default. */
      });
    return () => {
      active = false;
    };
  }, []);

  const setAppearance = useCallback((t: AppearanceTheme) => {
    setAppearanceState(t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {
      /* private mode — ignore */
    }
  }, []);

  const toggle = useCallback(() => {
    setAppearance(resolveDark(appearance) ? 'light' : 'dark');
  }, [appearance, setAppearance]);

  const value = useMemo<ThemeValue>(
    () => ({ appearance, setAppearance, isDark, toggle }),
    [appearance, setAppearance, isDark, toggle],
  );

  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
}
