import { css } from 'styled-components';

// Typography Functions
const fontType = (size, weight, lineHeight, letterSpacing) => css`
  font-weight: ${weight};
  font-size: ${size}px;
  line-height: ${lineHeight};
  text-decoration: none;
  letter-spacing: ${letterSpacing};
`;

const theme = {
  colors: {
    blue: {
      100: '#020C2B',
      200: '#0D307B',
      300: '#133e98',
      400: '#1f59d5',
      500: '#2568f5',
      600: '#528afa',
      700: '#7ca9fe',
      800: '#A7C6FF',
      900: '#d3e3ff',
    },
    pink: {
      100: '#412B42',
      200: '#5b3d5b',
      300: '#755076',
      400: '#ae79af',
      500: '#EBa4ec',
      600: '#f0b7f0',
      700: '#f4c9f4',
      800: '#f8dbf8',
      900: '#fcedfc',
    },
    teal: {
      100: '#002012',
      200: '#01603E',
      300: '#038F5F',
      400: '#04A870',
      500: '#06C282',
      600: '#42C98E',
      700: '#78D5A7',
      800: '#A2E2C0',
      900: '#DBF4E5',
    },
    green: {
      100: '#062012',
      200: '#0D341F',
      300: '#1F603D',
      400: '#33905D',
      500: '#48C380',
      600: '#61C98D',
      700: '#89D6A6',
      800: '#ACE2BF',
      900: '#def4e5',
    },
    red: {
      100: '#32100c',
      200: '#632118',
      300: '#953123',
      400: '#c6422f',
      500: '#f8523b',
      600: '#f97562',
      700: '#fb9789',
      800: '#fcbab1',
      900: '#fedcd8',
    },
    orange: {
      100: '#2D1100',
      200: '#622C02',
      300: '#9D4A05',
      400: '#DC6B0B',
      500: '#fd7c0f',
      600: '#FCAD48',
      700: '#FFA66F',
      800: '#FFCDAF',
      900: '#ffe6d7',
    }, 
    yellow: {
      100: '#453100',
      200: '#7C5A00',
      300: '#B88701',
      400: '#D89F01',
      500: '#F8B702',
      600: '#f9bf40',
      700: '#FDEF5E',
      800: '#FDE4B4',
      900: '#FEF1DA',
    },
    milk: {
      500:"#FEF8F3",
      700:"#fefaf7", 
    },
    grayscale: {
      100: '#121617', // Darkest gray/black
      300: '#353A3A', // Dark gray
      400: '#202020', // Darker gray
      500: '#BBBCBC', // Light gray
      700: '#eeeee', // Assuming a placeholder for lighter gray
      900: '#fcfcfc', // Lightest gray, matching the original theme's lightest
    },
    'black-alpha': {
      100: '#0000000a',
      200: '#00000014',
      300: '#00000029',
      400: '#0000003d',
      500: '#0000005c',
      600: '#0000007a',
      700: '#000000a3',
      800: '#000000cc',
      900: '#000000eb',
    },
    'white-alpha': {
      100: '#ffffff0a',
      200: '#ffffff14',
      300: '#ffffff29',
      400: '#ffffff3d',
      500: '#ffffff5c',
      600: '#ffffff7a',
      700: '#ffffffa3',
      800: '#ffffffcc',
      900: '#ffffffeb',
    },
  },

  typography: {
    /* Note that you are calling a function here, not an object */
    heading4xl: (weight = 700) => fontType(60, weight, '120%', '-2%'),
    heading3xl: (weight = 700) => fontType(48, weight, '125%', '-2%'),
    heading2xl: (weight = 700) => fontType(36, weight, '125%', '-1%'),
    headingXl: (weight = 700) => fontType(32, weight, '130%', '-1%'),
    headingLg: (weight = 700) => fontType(28, weight, '130%', '-1%'),
    headingMd: (weight = 700) => fontType(24, weight, '140%', '-1%'),
    headingSm: (weight = 700) => fontType(20, weight, '140%', '-1%'),
    headingXs: (weight = 700) => fontType(16, weight, '140%', '-1%'),
    textLg: (weight = 400) => fontType(18, weight, '160%', 'normal'),
    textMd: (weight = 400) => fontType(16, weight, '160%', 'normal'),
    textSm: (weight = 400) => fontType(14, weight, '160%', 'normal'),
  },

// Interfaces
  shadows: {
    lg: '4px 4px 0px 0px #000',
    md: '2px 2px 0px 0px #000',
    sm: '1px 1px 0px 0px #000',
  },

// Breakpoints
  breakpoints: {
    small: '480px', // Handphones
    medium: '768px', // Tablets
    large: '1024px', // Laptops 
    extra: '1440px', // Desktops
  },

  // Screen Widths
  widthConfig: {
    min: '320px',
    max: '2560px',
    container: '1920px',
  },

  // Function to extract colors- to refactor 
  getColor: (color, weight=500) => {
    return theme.colors[color] && theme.colors[color][weight] ? theme.colors[color][weight] : 'transparent';
  }
};



export default theme;