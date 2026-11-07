import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// En production, le backend sert l'interface compilée (frontend/dist).
// En développement (npm run dev), Vite relaie l'API vers le backend : python backend/launcher.py --browser
const BACKEND = 'http://127.0.0.1:8040';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { '/api': BACKEND, '/health': BACKEND },
  },
});
