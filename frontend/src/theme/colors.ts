import { createTheme } from '@mantine/core';

const colorTheme = createTheme({

  primaryColor: 'blue',
  primaryShade: 4,

  colors: {
    gray: [
      '#f7fafc', '#e4eef9', '#ccdaec', '#a9bcd0', '#73859c',
      '#43546c', '#364359', '#243044', '#1b2436', '#131b2c',
    ],

    blue: [
      '#d7e9ff', '#aed3ff', '#86beff', '#5da8ff', '#00f0ff',
      '#2a75cc', '#205899', '#153a66', '#0b1d33', '#000520', 
    ],
    green: [
      '#ddf5da', '#bcecb4', '#9ae28f', '#79d969', '#57cf44',
      '#46a636', '#347c29', '#23531b', '#11290e', '#091d06', 
    ],
    purple: [
      '#ecdffd', '#d9bffb', '#c69ef9', '#b37ef7', '#a05ef5',
      '#804bc4', '#603893', '#402662', '#201331', '#160d22', 
    ],
    red: [
      '#fedcd8', '#fcbab1', '#fb9789', '#f97562', '#f8523b',
      '#c6422f', '#953123', '#632118', '#32100c', '#230b08', 
    ],
    teal: [
      '#d9faf4', '#b3f5e9', '#8cefde', '#66ead3', '#40e5c8',
      '#33b7a0', '#268978', '#1a5c50', '#0d2e28', '#071f1b', 
    ],
    yellow: [
      '#fff1ce', '#ffe39d', '#ffd66c', '#ffc83b', '#ffba0a',
      '#cc9508', '#997006', '#664a04', '#332502', '#241a01', 
    ],

    // Custom alpha colors, padded to 10 shades
    'black-alpha': [
      '#0000000a', '#00000014', '#00000029', '#0000003d', '#0000005c',
      '#0000007a', '#000000a3', '#000000cc', '#000000eb', '#000000ff',
    ],
    'white-alpha': [
      '#ffffff0a', '#ffffff14', '#ffffff29', '#ffffff3d', '#ffffff5c',
      '#ffffff7a', '#ffffffa3', '#ffffffcc', '#ffffffeb', '#ffffffff', 
    ],
  },


  other: {
    background: '#ffffff',
    foreground: '#171717',
    backgroundBase: '#fbfcfd',
  },
});

export default colorTheme;