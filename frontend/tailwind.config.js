/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#003087',
          dark: '#001f5c',
          light: '#0050c8',
        },
      },
    },
  },
  plugins: [],
};
