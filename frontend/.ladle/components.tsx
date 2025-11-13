import React from "react";
import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import "@mantine/charts/styles.css";
import "@mantine/dates/styles.css";
import "@mantine/notifications/styles.css";
import customTheme from "@/theme";

// Wrap all Ladle stories with MantineProvider so Mantine components render correctly.
export const Provider = ({ children }: { children: React.ReactNode }) => (
  <MantineProvider theme={customTheme} defaultColorScheme="auto">
    {children}
  </MantineProvider>
);
