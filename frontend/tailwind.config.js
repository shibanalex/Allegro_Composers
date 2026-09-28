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
        display: ['var(--font-display)'],
        elegant: ['"EB Garamond"', 'Garamond', 'Georgia', 'serif'],
        caps: ['"Cormorant SC"', '"EB Garamond"', 'serif'],
        script: ['Tangerine', '"Great Vibes"', 'cursive'], // Great Vibes covers Cyrillic
      },
      colors: {
        // Values live in assets/css/styles.css (:root) so a hall's style (data-hall-theme) can redefine them
        ink: {
          950: 'rgb(var(--c-ink-950) / <alpha-value>)',
          900: 'rgb(var(--c-ink-900) / <alpha-value>)',
          850: 'rgb(var(--c-ink-850) / <alpha-value>)',
          800: 'rgb(var(--c-ink-800) / <alpha-value>)',
          700: 'rgb(var(--c-ink-700) / <alpha-value>)',
          600: 'rgb(var(--c-ink-600) / <alpha-value>)',
        },
        parchment: {
          DEFAULT: 'rgb(var(--c-parchment) / <alpha-value>)',
          muted: 'rgb(var(--c-parchment-muted) / <alpha-value>)',
          faint: 'rgb(var(--c-parchment-faint) / <alpha-value>)',
        },
        gold: {
          DEFAULT: 'rgb(var(--c-gold) / <alpha-value>)',
          light: 'rgb(var(--c-gold-light) / <alpha-value>)',
          dark: 'rgb(var(--c-gold-dark) / <alpha-value>)',
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
