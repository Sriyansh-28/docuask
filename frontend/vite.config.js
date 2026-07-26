import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend base URL is injected at build time via VITE_API_URL.
// In dev, requests to /api are proxied to the FastAPI server so the browser
// never hits a cross-origin URL locally.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
