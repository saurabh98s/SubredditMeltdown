/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
    "./src/app/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'scale-primary': 'var(--scale-primary)',
        'scale-primary-light': 'var(--scale-primary-light)',
        'scale-primary-dark': 'var(--scale-primary-dark)',
        'scale-accent': 'var(--scale-accent)',
        'scale-accent-light': 'var(--scale-accent-light)',
        'scale-accent-dark': 'var(--scale-accent-dark)',
        'scale-text-primary': 'var(--scale-text-primary)',
        'scale-text-secondary': 'var(--scale-text-secondary)',
        'scale-text-light': 'var(--scale-text-light)',
        'scale-bg-light': 'var(--scale-bg-light)',
        'scale-bg-dark': 'var(--scale-bg-dark)',
        'scale-border': 'var(--scale-border)',
        'scale-success': 'var(--scale-success)',
        'scale-warning': 'var(--scale-warning)',
        'scale-error': 'var(--scale-error)',
        'scale-info': 'var(--scale-info)',
      },
      boxShadow: {
        'scale': 'var(--scale-shadow)',
        'scale-md': 'var(--scale-shadow-md)',
        'scale-lg': 'var(--scale-shadow-lg)',
      },
      borderRadius: {
        'scale-sm': 'var(--scale-radius-sm)',
        'scale': 'var(--scale-radius)',
        'scale-md': 'var(--scale-radius-md)',
        'scale-lg': 'var(--scale-radius-lg)',
        'scale-xl': 'var(--scale-radius-xl)',
        'scale-2xl': 'var(--scale-radius-2xl)',
      },
      fontSize: {
        'scale-xs': 'var(--scale-text-xs)',
        'scale-sm': 'var(--scale-text-sm)',
        'scale-base': 'var(--scale-text-base)',
        'scale-lg': 'var(--scale-text-lg)',
        'scale-xl': 'var(--scale-text-xl)',
        'scale-2xl': 'var(--scale-text-2xl)',
        'scale-3xl': 'var(--scale-text-3xl)',
        'scale-4xl': 'var(--scale-text-4xl)',
      },
      lineHeight: {
        'scale-none': 'var(--scale-leading-none)',
        'scale-tight': 'var(--scale-leading-tight)',
        'scale-snug': 'var(--scale-leading-snug)',
        'scale-normal': 'var(--scale-leading-normal)',
        'scale-relaxed': 'var(--scale-leading-relaxed)',
        'scale-loose': 'var(--scale-leading-loose)',
      },
      spacing: {
        'scale-1': 'var(--scale-space-1)',
        'scale-2': 'var(--scale-space-2)',
        'scale-3': 'var(--scale-space-3)',
        'scale-4': 'var(--scale-space-4)',
        'scale-5': 'var(--scale-space-5)',
        'scale-6': 'var(--scale-space-6)',
        'scale-8': 'var(--scale-space-8)',
        'scale-10': 'var(--scale-space-10)',
        'scale-12': 'var(--scale-space-12)',
        'scale-16': 'var(--scale-space-16)',
      },
      transitionDuration: {
        'scale-fast': 'var(--scale-transition-fast)',
        'scale': 'var(--scale-transition)',
        'scale-slow': 'var(--scale-transition-slow)',
      },
    },
  },
  plugins: [],
  safelist: [
    'bg-blue-500',
    'bg-green-500',
    'bg-red-500',
    'bg-purple-500',
    'bg-yellow-500',
    'bg-gray-500',
  ],
}; 