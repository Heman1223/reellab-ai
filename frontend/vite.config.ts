import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // The contracts and the fixtures both live outside `frontend/`. Types are
      // erased at build time; the JSON fixtures are inlined into the bundle.
      '@shared': fileURLToPath(new URL('../shared', import.meta.url)),
      '@data': fileURLToPath(new URL('../data', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    fs: {
      // Let the dev server read `shared/` and `data/`, which sit above the root.
      allow: [fileURLToPath(new URL('..', import.meta.url))],
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
