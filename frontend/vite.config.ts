import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During development the API is proxied to the Flask assistant.
// In production the assistant serves the built files from ../assistant/static.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:5007',
        changeOrigin: true,
      },
    },
  },
});
