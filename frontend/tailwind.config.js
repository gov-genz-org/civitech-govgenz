/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        gov: {
          bg: 'var(--ggz-bg)',
          surface: 'var(--ggz-surface)',
          surfaceSoft: 'var(--ggz-surface-soft)',
          card: 'var(--ggz-card)',
          border: 'var(--ggz-border)',
          text: 'var(--ggz-text)',
          muted: 'var(--ggz-text-muted)',
          soft: 'var(--ggz-text-soft)',
          primary: 'var(--ggz-primary)',
          primaryDark: 'var(--ggz-primary-dark)',
          primarySoft: 'var(--ggz-primary-soft)',
          accent: 'var(--ggz-accent)',
          accentDark: 'var(--ggz-accent-dark)',
          accentSoft: 'var(--ggz-accent-soft)',
          warning: 'var(--ggz-warning)',
          success: 'var(--ggz-success)',
          danger: 'var(--ggz-danger)',
        },
      },
      fontFamily: {
        title: ['Oswald', 'Barlow Condensed', 'system-ui', 'sans-serif'],
        mono: ['Space Mono', 'IBM Plex Mono', 'JetBrains Mono', 'monospace'],
      },
      letterSpacing: {
        widest: '0.2em',
      },
    },
  },
  plugins: [],
}
