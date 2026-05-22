import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import ruRU from "antd/locale/ru_RU";
import App from "./App";
import { ThemeProvider } from "./design/ThemeContext";
import { FavoritesProvider } from "./contexts/FavoritesContext";
import { TimeScopeProvider } from "./contexts/TimeScopeContext";
import "./i18n";

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
        <ConfigProvider locale={ruRU} theme={{ token: { colorPrimary: "#0969da" } }}>
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
