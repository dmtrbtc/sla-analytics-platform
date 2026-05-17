import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-antd": ["antd", "@ant-design/icons"],
          "vendor-echarts": ["echarts", "echarts-for-react"],
          "vendor-query": ["@tanstack/react-query", "zustand"],
        },
      },
    },
  },
});
