/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Agentica Warm Editorial Palette
        canvas: '#E8E3DA',          // Main warm ivory background
        surface: {
          DEFAULT: '#F7F4EE',       // Primary surface (cards, modals, tables)
          secondary: '#DED8CD',     // Secondary surface (chips, subtle bars)
          subtle: '#EDE8DF',        // Subtle panel insets
          pure: '#FFFFFF',          // High-contrast input / elevated elements
        },
        burgundy: {
          DEFAULT: '#7D292D',       // Primary brand action, buttons, active tabs
          dark: '#612024',          // Hover / active pressed
          light: '#9E393E',         // Lighter accent
          subtle: '#F4ECEB',        // Tinted badge / pill background
        },
        sage: {
          DEFAULT: '#A8B3A1',       // Visualizations, secondary accents
          light: '#D7DED1',         // Soft chart backgrounds and panels
          dark: '#586452',          // Readable text on light sage
          subtle: '#EEF2EB',        // Soft badge background
        },
        taupe: {
          DEFAULT: '#82786F',       // Supporting text and labels
          light: '#A69E96',         // Muted secondary hints
          dark: '#4D443D',          // Deeper readable taupe
        },
        ink: {
          DEFAULT: '#241B19',       // Primary headings, numbers, body
          secondary: '#82786F',     // Secondary body / metadata
          muted: '#A69E96',         // Tertiary / hints
        },
        border: {
          DEFAULT: '#CFC7BB',       // Card borders, dividers, inputs
          subtle: '#E2DBD0',        // Extremely fine dividers
          strong: '#B3AAA0',        // Interactive borders / focus
        },
        orange: {
          DEFAULT: '#F36B32',       // Vivid brand accent
          subtle: '#FDEEE8',        // Accent chip background
        },
        // Semantic states
        success: {
          DEFAULT: '#38865B',
          bg: '#E4EFE8',
          border: '#B2D5C1',
        },
        warning: {
          DEFAULT: '#A86E24',
          bg: '#FBF2E5',
          border: '#E8CEA7',
        },
        danger: {
          DEFAULT: '#B84040',
          bg: '#FBEBEB',
          border: '#E9B3B3',
        },
      },
      fontFamily: {
        serif: ['"DM Serif Display"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'warm-sm': '0 1px 2px rgba(36, 27, 25, 0.04)',
        'warm-md': '0 4px 12px rgba(36, 27, 25, 0.06)',
        'warm-lg': '0 10px 24px rgba(36, 27, 25, 0.08)',
        'warm-xl': '0 20px 36px rgba(36, 27, 25, 0.10)',
      },
    },
  },
  plugins: [],
}
