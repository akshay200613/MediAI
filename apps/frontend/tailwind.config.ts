import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
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
        /* Ivory (auth panel light mode) */
        ivory: {
          50:  '#fefdfb',
          100: '#fdf8f0',
          200: '#f5f0e8',
          300: '#e8e0d4',
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
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-gradient': 'linear-gradient(135deg, #0a0f1e 0%, #0d1526 50%, #111827 100%)',
        'teal-gradient': 'linear-gradient(135deg, #0d9488 0%, #14b8a6 50%, #2dd4bf 100%)',
        'teal-gradient-hover': 'linear-gradient(135deg, #0f766e 0%, #0d9488 50%, #14b8a6 100%)',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0, 0, 0, 0.3)',
        glow: '0 0 20px rgba(20, 184, 166, 0.3)',
        'glow-lg': '0 0 40px rgba(20, 184, 166, 0.4)',
        'glow-accent': '0 0 20px rgba(6, 182, 212, 0.3)',
        'card-hover': '0 12px 40px rgba(0, 0, 0, 0.3)',
      },
      width: {
        'sidebar-collapsed': '72px',
        'sidebar-expanded': '240px',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'typing-cursor': 'blink 530ms steps(1) infinite',
        'shimmer': 'shimmer 1.5s ease-in-out infinite',
        'gradient-rotate': 'gradientRotate 3s linear infinite',
        'mesh-drift-1': 'meshDrift1 12s ease-in-out infinite',
        'mesh-drift-2': 'meshDrift2 15s ease-in-out infinite',
        'mesh-drift-3': 'meshDrift3 10s ease-in-out infinite',
        'mesh-scale-1': 'meshScale1 10s ease-in-out infinite',
        'mesh-scale-2': 'meshScale2 12s ease-in-out infinite',
        'float-particle': 'floatParticle 6s ease-in-out infinite',
        'bell-shake': 'bellShake 400ms ease-in-out',
        'bounce-dot': 'bounceDot 1.4s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'logo-pulse': 'logoPulse 4s ease-in-out infinite',
        'breathe': 'breathe 3s ease-in-out infinite',
        'draw-line': 'drawLine 1.2s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        gradientRotate: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        meshDrift1: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '33%': { transform: 'translate(30px, -20px)' },
          '66%': { transform: 'translate(-20px, 15px)' },
        },
        meshDrift2: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '33%': { transform: 'translate(-25px, 25px)' },
          '66%': { transform: 'translate(20px, -30px)' },
        },
        meshDrift3: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(15px, 20px)' },
        },
        meshScale1: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.15)' },
        },
        meshScale2: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.1)' },
        },
        floatParticle: {
          '0%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '50%': { transform: 'translateY(-20px)', opacity: '0.8' },
        },
        bellShake: {
          '0%, 100%': { transform: 'rotateZ(0)' },
          '15%': { transform: 'rotateZ(15deg)' },
          '30%': { transform: 'rotateZ(-15deg)' },
          '45%': { transform: 'rotateZ(10deg)' },
          '60%': { transform: 'rotateZ(-10deg)' },
          '75%': { transform: 'rotateZ(5deg)' },
        },
        bounceDot: {
          '0%, 80%, 100%': { transform: 'translateY(0)' },
          '40%': { transform: 'translateY(-6px)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(20, 184, 166, 0.2)' },
          '50%': { boxShadow: '0 0 25px rgba(20, 184, 166, 0.5)' },
        },
        logoPulse: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.03)' },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.02)' },
        },
        drawLine: {
          '0%': { strokeDashoffset: '1' },
          '100%': { strokeDashoffset: '0' },
        },
      },
    },
  },
  plugins: [],
}

export default config
