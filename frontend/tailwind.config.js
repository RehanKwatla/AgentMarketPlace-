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
          bg: '#0B0D0D',
          secondary: '#101313',
          card: 'rgba(16, 22, 22, 0.88)',
          elevated: '#141A19',
          input: '#0D1111',
          border: 'rgba(120, 160, 153, 0.20)',
          borderStrong: 'rgba(160, 190, 183, 0.38)',
          text: '#F4F7F6',
          secondaryText: '#A0AAA7',
          mutedText: '#6F7C78',
          accent: '#36D6C8',
          accentHover: '#53E3D6',
          deepTeal: '#124A45',
          success: '#42C995',
          warning: '#E7B96A',
          error: '#E16D6D',
        },
      },
    },
  },
  plugins: [],
}
