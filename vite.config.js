import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? '/Expert_system_backend/' : '/',
  server: {
    port: 3000,
    proxy: {
       '/auth':     process.env.VITE_AUTH_PROXY_TARGET || 'https://expert-system-431h.onrender.com',
       '/content':  process.env.VITE_CONTENT_PROXY_TARGET || 'https://expert-system-431h.onrender.com',
       '/tests':    process.env.VITE_TESTS_PROXY_TARGET || 'https://expert-system-431h.onrender.com',
       '/sessions': process.env.VITE_SESSIONS_PROXY_TARGET || 'https://expert-system-431h.onrender.com',
      // '/auth':     'http://localhost:8001',
      // '/content':  'http://localhost:8002',
      // '/tests':    'http://localhost:8003',
      // '/sessions': 'http://localhost:8004',
    },
  },
}));
