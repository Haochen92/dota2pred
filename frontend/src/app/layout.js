import './globals.css';
import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

import localFont from 'next/font/local';
import { ColorSchemeScript, mantineHtmlProps } from '@mantine/core';
import Providers from './Providers';

// Default document metadata for every route. Page files override `title` via the template
// (e.g. "Match Tracker | Dota Oracle") and may set their own description.
export const metadata = {
  title: {
    default: 'Dota Oracle',
    template: '%s | Dota Oracle',
  },
  description:
    'Real-time Dota 2 match outcome prediction: live pro-match predictions, an interactive draft predictor, and model performance analytics.',
};

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
