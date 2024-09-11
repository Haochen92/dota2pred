"use client";

import StyledComponentsRegistry from "lib/registry";
import GlobalStyle from "@styles/GlobalStyle";
import { ThemeProvider } from "styled-components";
import theme from "@styles/theme";

const metadata = {
  title: "Dota 2 Match Predictor",
  description: "A Single Page Web application which predict the outcome of professional Dota 2 matches",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
          <meta charSet="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>{metadata.title}</title>
          <meta name="description" content={metadata.description} />
      </head>
      <body>
        <StyledComponentsRegistry>
          <ThemeProvider theme={theme}>
            <GlobalStyle />
            {children}
          </ThemeProvider> 
        </StyledComponentsRegistry>
      </body>
    </html>
  );
}
