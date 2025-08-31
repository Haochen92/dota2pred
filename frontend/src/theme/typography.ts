import { createTheme, rem, Text } from '@mantine/core';

const typographyTheme = createTheme({
  fontFamily: 'var(--my-font), sans-serif',
  
  headings: {
    fontFamily: 'var(--my-font), sans-serif',
    fontWeight: '700', 
    sizes: {
      // .heading4xl -> h1
      h1: { fontSize: rem(60), lineHeight: '1.2' },
      // .heading3xl -> h2
      h2: { fontSize: rem(48), lineHeight: '1.25' },
      // .heading2xl -> h3
      h3: { fontSize: rem(36), lineHeight: '1.25' },
      // .headingxl -> h4
      h4: { fontSize: rem(32), lineHeight: '1.3' },
      // .headinglg -> h5
      h5: { fontSize: rem(28), lineHeight: '1.3' },
      // .headingmd -> h6
      h6: { fontSize: rem(24), lineHeight: '1.4' },
    },
  },

   /**
   * 3. FONT SIZES (for Text component and fz prop)
   */
  fontSizes: {
    xs: rem(14), 
    sm: rem(15), 
    md: rem(16), 
    lg: rem(18), 
    xl: rem(20), 
  },

  lineHeights: {
    xs: '1.6', 
    sm: '1.6', 
    md: '1.55', 
    lg: '1.6', 
    xl: '1.5', 
  },


  shadows: {
    sm: '1px 1px 0px #000000',
    md: '0px 0px 8px rgba(0, 0, 0, 0.5)',
    lg: '4px 4px 0px #000000, 0px 4px 4px rgba(27, 30, 34, 0.06)',
  }
});

export default typographyTheme;


