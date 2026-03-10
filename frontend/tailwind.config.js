/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'system-ui', 'sans-serif'],
      },
      colors: {
        navy: {
          DEFAULT: '#1d1464',
          50: '#ebebf8', 100: '#c5c4ed', 200: '#9f9ce2',
          300: '#7975d7', 400: '#534ecc', 500: '#1d1464',
          600: '#191059', 700: '#140d47', 800: '#100a38', 900: '#0b0728',
        },
        purple: {
          DEFAULT: '#4527a0',
          50: '#ede9f8', 100: '#ccc2ef', 200: '#ab9ae5',
          300: '#8a72db', 400: '#694bd2', 500: '#4527a0',
          600: '#3b208e', 700: '#2e1970', 800: '#231454', 900: '#180e39',
        },
        pink: {
          DEFAULT: '#e01e8c',
          50: '#fde9f5', 100: '#f9c0e2', 200: '#f597ce',
          300: '#f06eba', 400: '#eb45a6', 500: '#e01e8c',
          600: '#c7197d', 700: '#9e1462', 800: '#750f49', 900: '#4d0a30',
        },
        orange: {
          DEFAULT: '#f5821e',
          50: '#fef4e9', 100: '#fde0be', 200: '#fbcc94',
          300: '#f9b86a', 400: '#f7a440', 500: '#f5821e',
          600: '#dc741a', 700: '#b05c14', 800: '#84440f', 900: '#582d0a',
        },
      },
      backgroundImage: {
        'gradient-brand':      'linear-gradient(135deg, #1d1464 0%, #4527a0 45%, #e01e8c 100%)',
        'gradient-brand-soft': 'linear-gradient(135deg, #4527a0 0%, #e01e8c 100%)',
        'gradient-brand-pale': 'linear-gradient(135deg, #ede9f8 0%, #fde9f5 100%)',
      },
      boxShadow: {
        brand: '0 4px 24px -4px rgba(224,30,140,0.30)',
        card:  '0 2px 12px -2px rgba(29,20,100,0.10)',
      },
    },
  },
  plugins: [],
};
