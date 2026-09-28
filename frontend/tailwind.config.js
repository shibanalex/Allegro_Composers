/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app.vue",
    "./error.vue",
    "./components/**/*.{vue,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./composables/**/*.ts",
    "./utils/**/*.ts",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"EB Garamond"', 'Garamond', 'Georgia', 'serif'],
        // Russian book type of the 19th century: aristocratic, with a calm italic and even figures in Cyrillic
        display: ['"Old Standard TT"', '"EB Garamond"', 'Georgia', 'serif'],
        elegant: ['"EB Garamond"', 'Garamond', 'Georgia', 'serif'],
        caps: ['"Cormorant SC"', '"EB Garamond"', 'serif'],
        script: ['Tangerine', '"Great Vibes"', 'cursive'], // Great Vibes covers Cyrillic
      },
      colors: {
        ink: {
          950: '#050403',
          900: '#0a0807',
          850: '#100c0a',
          800: '#16110e',
          700: '#211914',
          600: '#34281f',
        },
        parchment: {
          DEFAULT: '#e9dfc9',
          muted: '#b8aa8e',
          faint: '#8a7d66',
        },
        gold: {
          DEFAULT: '#c9a36a',
          light: '#e0c28c',
          dark: '#9c7a45',
        },
        wine: '#7a3434',
        oxblood: '#3d1010',
      },
      maxWidth: {
        prose: '42rem',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-up': 'fade-up .7s ease-out both',
      },
    },
  },
  plugins: [],
}
