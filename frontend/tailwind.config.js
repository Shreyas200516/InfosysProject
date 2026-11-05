/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Brand
        sidebar: '#1E293B',
        primary: { DEFAULT: '#F97316', hover: '#EA580C' },
        page: '#F8FAFC',
        card: '#FFFFFF',
        ai: '#FFF7ED',
        heading: '#0F172A',
        secondary: '#64748B',
        line: '#E2E8F0',
        // Ticket status colours: separate from the brand colours on purpose
        status: { critical: '#DC2626', high: '#F97316', medium: '#EAB308', low: '#2563EB', resolved: '#16A34A' },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['"Instrument Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgba(15,23,42,0.04), 0 1px 3px 0 rgba(15,23,42,0.06)',
        pop: '0 10px 30px -12px rgba(15,23,42,0.25)',
      },
    },
  },
  plugins: [],
}
