import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/TestingExpertSystem/',
  server: {
    port: 3000,
    proxy: {
      '/auth':     'https://expert-system-431h.onrender.com',
      '/content':  'https://expert-system-431h.onrender.com',
      '/tests':    'https://expert-system-431h.onrender.com',
      '/sessions': 'https://expert-system-431h.onrender.com',
    },
  },
});
