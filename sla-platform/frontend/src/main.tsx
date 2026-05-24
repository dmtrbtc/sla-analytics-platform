import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import ruRU from "antd/locale/ru_RU";
import * as echarts from "echarts/core";
import App from "./App";
import { ThemeProvider } from "./design/ThemeContext";
import { FavoritesProvider } from "./contexts/FavoritesContext";
import { TimeScopeProvider } from "./contexts/TimeScopeContext";
import {
  slaTheme,
  slaEChartsTheme,
  SLA_ECHARTS_THEME_NAME,
} from "./design";
import "./design/tokens.css";
import "./i18n";

// Register the canonical SLA ECharts theme exactly once at module load time.
// Every <ReactECharts theme="sla" /> in the app pulls colors/typography/grid
// styles from here. Do NOT override colors per-chart — extend the theme.
echarts.registerTheme(SLA_ECHARTS_THEME_NAME, slaEChartsTheme);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={ruRU} theme={slaTheme}>
          <BrowserRouter>
            <TimeScopeProvider>
              <FavoritesProvider>
                <App />
              </FavoritesProvider>
            </TimeScopeProvider>
          </BrowserRouter>
        </ConfigProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>
);
