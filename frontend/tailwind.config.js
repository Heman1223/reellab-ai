/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#fdfbf7', // Cream page background
          800: '#ffffff', // White
          700: '#e7e5df', // Borders
          600: '#d6d3cc', // Darker borders
          500: '#a3a099', // Muted text
        },
        accent: {
          DEFAULT: '#d75d4e', // Coral/terracotta
          soft: '#e8897d',
          dim: '#f3ece9',
        },
        signal: {
          strong: '#10b981',
          mixed: '#f59e0b',
          weak: '#d75d4e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        serif: ['Georgia', 'Cambria', '"Times New Roman"', 'Times', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
};
