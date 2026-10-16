import { defineConfig } from "vite";

const API = "http://127.0.0.1:8765";
const proxy = { "/api": { target: API, changeOrigin: true } };

export default defineConfig({
  server: { host: "127.0.0.1", port: 5190, strictPort: true, proxy },
  preview: { host: "127.0.0.1", port: 4190, strictPort: true, proxy },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: "index.html",
        brak: "404.html",
        polityka: "polityka-prywatnosci.html",
        regulamin: "regulamin.html",
      },
    },
  },
});
