import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'rgba(30, 41, 59, 0.8)',
        /* Brand – Teal primary */
        primary: {
          50:  '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        /* Accent – Cyan/Sky */
        accent: {
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
        /* Dark surfaces */
        surface: {
          900: '#0a0f1e',
          800: '#0d1526',
          700: '#111827',
          600: '#1a2332',
          500: '#1f2d3d',
          400: '#2a3a50',
        },
        /* Amber callouts */
        callout: {
          amber:  '#f59e0b',
          'amber-bg': 'rgba(245, 158, 11, 0.08)',
          'amber-border': 'rgba(245, 158, 11, 0.25)',
          red: '#ef4444',
          'red-bg': 'rgba(239, 68, 68, 0.08)',
          'red-border': 'rgba(239, 68, 68, 0.25)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
