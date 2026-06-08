import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: process.env.VITE_BASE || '/',
  server: {
    port: 3000,
    proxy: {
      '/auth':     'http://localhost:8001',
      '/content':  'http://localhost:8002',
      '/tests':    'http://localhost:8003',
      '/sessions': 'http://localhost:8004',
    },
  },
}));
