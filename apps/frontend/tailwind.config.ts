import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'primary-dark': '#1A0A2A',
        'primary-medium': '#381E57',
        'primary-light': '#572F8B',
        'accent-gold': '#D4AF37',
        'accent-light': '#FFD700',
        'text-light': '#E0E0E0',
        'text-medium': '#B0B0B0',
        'text-dark': '#808080',
        success: '#34C759',
        warning: '#FF9500',
        'warning-dark': '#CC7700',
        error: '#FF453A',
        info: '#0A84FF',
        'info-dark': '#0765C7',
      },
      fontFamily: {
        manrope: ['var(--font-manrope)', 'sans-serif'],
        inter: ['var(--font-inter)', 'sans-serif'],
        poppins: ['var(--font-poppins)', 'sans-serif'],
      },
      boxShadow: {
        '3xl': '0 35px 60px -15px rgba(0, 0, 0, 0.3)',
      },
    },
  },
  plugins: [],
}

export default config
