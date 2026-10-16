/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          bg: '#0A0A0A',
          secondary: '#111111',
          card: 'rgba(18, 18, 18, 0.88)',
          elevated: '#141414',
          input: '#0D0D0D',
          border: 'rgba(255, 255, 255, 0.12)',
          borderStrong: 'rgba(255, 255, 255, 0.28)',
          text: '#FAFAFA',
          secondaryText: '#A3A3A3',
          mutedText: '#737373',
          accent: '#FFFFFF',
          accentHover: '#E5E5E5',
          deepTeal: '#262626',
          success: '#D4D4D4',
          warning: '#A3A3A3',
          error: '#737373',
        },
      },
    },
  },
  plugins: [],
}
