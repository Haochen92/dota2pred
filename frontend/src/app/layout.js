import './globals.css';
import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

import localFont from 'next/font/local';
import { ColorSchemeScript, mantineHtmlProps } from '@mantine/core';
import Providers from './Providers';

const Apercu = localFont({
  src: [
    {
      path: 'fonts/ApercuBold.otf',
      weight: '700',
      style: 'normal',
    },
    {
      path: 'fonts/ApercuMedium.otf',
      weight: '500',
      style: 'normal',
    },
    {
      path: 'fonts/ApercuRegular.otf',
      weight: '400',
      style: 'normal',
    },
  ],
  variable: '--my-font',
});


export default function RootLayout({ children, modal }) {
  return (
    <html lang="en" {...mantineHtmlProps}>
      <head>
        <ColorSchemeScript defaultColorScheme="auto" />
      </head>
      <body className={`${Apercu.className} ${Apercu.variable}`}>
        <Providers modal={modal}>{children}</Providers>
      </body>
    </html>
  );
}
