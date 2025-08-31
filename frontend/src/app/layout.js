'use client';

import './globals.css';
import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

import localFont from 'next/font/local';
import { ColorSchemeScript, MantineProvider, AppShell, mantineHtmlProps } from '@mantine/core';
import customTheme from '@/theme/index';
import Navbar from '@/components/nav/Navbar';

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


export default function RootLayout({ children }) {
  return (
    <html lang="en" {...mantineHtmlProps}>
      <head>
        <ColorSchemeScript defaultColorScheme="auto" />
      </head>
      <body className={`${Apercu.className} ${Apercu.variable}`}>
        <MantineProvider theme={customTheme} defaultColorScheme="auto">
          <AppShell header={{ height: 80, offset: true }}>
            <AppShell.Header>
              <Navbar />
            </AppShell.Header>
            <AppShell.Main
              bg="blue.9"
            >
              {children}
            </AppShell.Main>
          </AppShell>
        </MantineProvider>
      </body>
    </html>
  );
}
