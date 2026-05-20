import { createContext, useContext, useState, useEffect, useCallback, useMemo, type ReactNode } from "react";
import { palette, darkPalette } from "./colors";
import { shadows, darkShadows } from "./shadows";
import { chartTheme, darkChartTheme } from "./chartTheme";

type ThemeMode = "light" | "dark" | "system";

interface ThemeContextValue {
  mode: ThemeMode;
  resolved: "light" | "dark";
  setMode: (m: ThemeMode) => void;
  colors: Record<string, any>;
  shadows: Record<string, string>;
  chartTheme: Record<string, any>;
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: "system",
  resolved: "light",
  setMode: () => {},
  colors: palette,
  shadows: shadows,
  chartTheme: chartTheme,
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => (localStorage.getItem("sla-theme") as ThemeMode) || "system");
  const [systemDark, setSystemDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const resolved = mode === "system" ? (systemDark ? "dark" : "light") : mode;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.style.colorScheme = resolved;
  }, [resolved]);

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m);
    localStorage.setItem("sla-theme", m);
  }, []);

  const value = useMemo(() => ({
    mode,
    resolved,
    setMode,
    colors: resolved === "dark" ? darkPalette : palette,
    shadows: resolved === "dark" ? darkShadows : shadows,
    chartTheme: resolved === "dark" ? darkChartTheme : chartTheme,
  }), [mode, resolved, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
