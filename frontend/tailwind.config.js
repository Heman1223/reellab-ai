/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Named by role, not by hue, so a restyle does not mean editing every
        // component.
        ink: {
          900: '#0b0c10',
          800: '#12141a',
          700: '#1a1d26',
          600: '#252935',
          500: '#343a4a',
        },
        accent: {
          DEFAULT: '#7c8cff',
          soft: '#a5b0ff',
          dim: '#4d59b8',
        },
        signal: {
          strong: '#3ecf8e',
          mixed: '#e6b450',
          weak: '#f2668b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
};
