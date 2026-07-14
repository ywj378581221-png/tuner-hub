import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [vue()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/media": "http://127.0.0.1:8000",
      "/static/assets": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "backend/static",
    emptyOutDir: true,
  },
}));
