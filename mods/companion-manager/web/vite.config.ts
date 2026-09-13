import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  plugins: [react()],
  server: { watch: { usePolling: true, interval: 300 } },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
