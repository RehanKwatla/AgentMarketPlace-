/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ivory: {
          DEFAULT: '#F1EFE7',
          deep: '#EAE7DC',
        },
        ink: {
          DEFAULT: '#20231F',
          soft: '#3A3E38',
        },
        mute: '#77776E',
        taupe: '#D4C4A8',
        champagne: '#F2D58A',
        gold: '#C9A961',
        surface: '#FAF9F4',
        hairline: '#DAD7CC',
      },
      fontFamily: {
        display: ['"Iowan Old Style"', '"Palatino Linotype"', 'Palatino', 'Georgia', 'serif'],
        sans: ['Inter', '"Segoe UI"', 'system-ui', '-apple-system', '"Helvetica Neue"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.03em',
      },
      boxShadow: {
        surface: '0 1px 2px rgba(32,35,31,0.04), 0 12px 32px -18px rgba(32,35,31,0.18)',
        lifted: '0 2px 4px rgba(32,35,31,0.05), 0 28px 60px -32px rgba(32,35,31,0.28)',
        halo: '0 0 0 1px rgba(218,215,204,0.9), 0 20px 50px -30px rgba(201,169,97,0.45)',
      },
      maxWidth: {
        prose: '42rem',
      },
    },
  },
  plugins: [],
};
