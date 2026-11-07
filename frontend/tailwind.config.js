import nightNavy from 'night-navy/tailwind-v3-preset';

/** Couleurs, police et arrondis : design system commun Night Navy (github:aminart/Design-system-). */
/** @type {import('tailwindcss').Config} */
export default {
  presets: [nightNavy],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  plugins: [],
};
