/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F2EEE5', surface: '#FBF9F4', surface2: '#F1EBDF',
        ink: '#1B1A17', inkSoft: '#6E6A63', line: '#E5DFD2',
        coral: '#CC785C', coralDeep: '#B05E40', brick: '#B2553B',
        olive: '#7E8C57', ochre: '#BC8A2E', clay: '#9A6A4F', coralTint: '#F6E6DE',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['"Hanken Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
