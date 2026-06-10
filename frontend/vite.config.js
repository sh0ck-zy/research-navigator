import { defineConfig } from 'vite';

// data/ is served by Vite in dev (it lives under the project root) and by
// FastAPI's /data mount in production, so it is not copied into dist.
export default defineConfig({
  publicDir: false,
  optimizeDeps: {
    exclude: ['gsap'],
  },
  server: {
    port: 5173,
    proxy: {
      // 127.0.0.1 explicitly — localhost can resolve to ::1, where Docker publishes :8000
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
