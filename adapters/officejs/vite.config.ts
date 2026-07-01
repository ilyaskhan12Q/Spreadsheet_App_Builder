import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    headers: {
      "Access-Control-Allow-Origin": "*",
    }
  },
  build: {
    rollupOptions: {
      input: {
        taskpane: 'taskpane.html'
      }
    }
  },
  test: {
    globals: true,
    environment: 'node',
  }
} as any);
