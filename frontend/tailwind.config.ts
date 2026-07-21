/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // SafetyIQ design system
        surface: {
          950: '#080C10',
          900: '#0D1117',
          800: '#131920',
          700: '#1A2230',
          600: '#1E2B3C',
        },
        risk: {
          safe:     '#22C55E',
          caution:  '#EAB308',
          elevated: '#F97316',
          danger:   '#EF4444',
          critical: '#DC2626',
        },
        accent: {
          blue:   '#3B82F6',
          cyan:   '#06B6D4',
          amber:  '#F59E0B',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink':      'blink 1.2s step-end infinite',
        'scan':       'scan 4s linear infinite',
      },
      keyframes: {
        blink: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0 } },
        scan:  { '0%': { transform: 'translateY(-100%)' }, '100%': { transform: 'translateY(100%)' } },
      },
    },
  },
  plugins: [],
}