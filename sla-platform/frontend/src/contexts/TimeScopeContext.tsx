import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";
import { useLocation, useNavigate } from "react-router-dom";

/**
 * Global forensic time-scope. Drives every analytics query in the app.
 *
 * Persistence:
 *   1. URL query params (?period=7d  or  ?since=...&until=...)
 *      → first source of truth so links are shareable
 *   2. localStorage (sla.timeScope)
 *      → fallback when the URL has no scope
 *
 * The page that consumes a query just calls useTimeScope().toParams() and
 * spreads that into the axios `params` field. The backend's parse_time_scope
 * does the same precedence (period > since/until > all-time).
 */

export type ScopePreset = "all" | "1d" | "24h" | "7d" | "30d" | "90d" | "custom";

export interface TimeScopeState {
  preset: ScopePreset;
  /** ISO timestamps for custom mode; ignored when preset != "custom" */
  since?: string;
  until?: string;
}

interface TimeScopeCtx extends TimeScopeState {
  setPreset: (preset: ScopePreset) => void;
  setCustomRange: (since: string, until: string) => void;
  /** Returns an object ready to spread into axios `params` */
  toParams: () => Record<string, string | undefined>;
  /** Human-readable label for the current scope (RU). */
  label: string;
}

const Ctx = createContext<TimeScopeCtx | null>(null);

const STORAGE_KEY = "sla.timeScope";
const URL_PERIOD = "period";
const URL_SINCE = "since";
const URL_UNTIL = "until";

const PRESET_LABELS: Record<ScopePreset, string> = {
  all:    "Всё время",
  "1d":   "Последние 24 ч",
  "24h":  "Последние 24 ч",
  "7d":   "7 дней",
  "30d":  "30 дней",
  "90d":  "90 дней",
  custom: "Custom",
};

function readUrl(search: string): TimeScopeState | null {
  const p = new URLSearchParams(search);
  const period = p.get(URL_PERIOD);
  const since = p.get(URL_SINCE) || undefined;
  const until = p.get(URL_UNTIL) || undefined;
  if (period && ["all", "1d", "24h", "7d", "30d", "90d"].includes(period)) {
    return { preset: period as ScopePreset };
  }
  if (since && until) {
    return { preset: "custom", since, until };
  }
  return null;
}

function readStorage(): TimeScopeState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as TimeScopeState;
    if (parsed && parsed.preset) return parsed;
  } catch { /* ignore */ }
  return null;
}

function writeStorage(state: TimeScopeState): void {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* ignore */ }
}

export function TimeScopeProvider({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();

  // Initial state: URL → storage → all-time default
  const [state, setState] = useState<TimeScopeState>(() => {
    return readUrl(location.search) ?? readStorage() ?? { preset: "all" };
  });

  // Mirror state into URL query params so the link is shareable
  // (and bookmarkable). We strip the keys we own and rebuild them.
  useEffect(() => {
    const p = new URLSearchParams(location.search);
    p.delete(URL_PERIOD); p.delete(URL_SINCE); p.delete(URL_UNTIL);
    if (state.preset === "custom" && state.since && state.until) {
      p.set(URL_SINCE, state.since);
      p.set(URL_UNTIL, state.until);
    } else if (state.preset !== "all") {
      p.set(URL_PERIOD, state.preset);
    }
    const next = p.toString();
    const targetSearch = next ? `?${next}` : "";
    if (targetSearch !== location.search) {
      // replace, not push — we don't want a back-history entry per scope tweak
      navigate({ pathname: location.pathname, search: targetSearch }, { replace: true });
    }
    writeStorage(state);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.preset, state.since, state.until]);

  const setPreset = useCallback((preset: ScopePreset) => {
    setState((s) => {
      // moving away from custom drops since/until
      if (preset !== "custom") return { preset };
      return { ...s, preset };
    });
  }, []);

  const setCustomRange = useCallback((since: string, until: string) => {
    setState({ preset: "custom", since, until });
  }, []);

  const toParams = useCallback((): Record<string, string | undefined> => {
    if (state.preset === "all") return {};
    if (state.preset === "custom" && state.since && state.until) {
      return { since: state.since, until: state.until };
    }
    return { period: state.preset };
  }, [state]);

  const label = useMemo(() => {
    if (state.preset === "custom" && state.since && state.until) {
      const s = state.since.slice(0, 10);
      const u = state.until.slice(0, 10);
      return `${s} → ${u}`;
    }
    return PRESET_LABELS[state.preset];
  }, [state]);

  const value: TimeScopeCtx = {
    ...state, setPreset, setCustomRange, toParams, label,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTimeScope(): TimeScopeCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useTimeScope must be used inside TimeScopeProvider");
  return v;
}
