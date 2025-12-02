'use client';

import { ReactNode } from 'react';
import { MantineProvider, AppShell, Container, Flex } from '@mantine/core';
import QueryProvider from '@/context/QueryProvider';
import customTheme from '@/theme/index';
import Navbar from '@/components/nav/Navbar';

interface ProvidersProps {
  children: ReactNode;
  modal: ReactNode;
}

export default function Providers({ children, modal }: ProvidersProps) {
  return (
    <QueryProvider>
      <MantineProvider theme={customTheme} defaultColorScheme="auto">
        <AppShell header={{ height: 80, offset: true }}>
          <AppShell.Header bg="gray.9">
            <Flex align="center" justify="center" h="100%">
              <Navbar />
            </Flex>
          </AppShell.Header>
          <AppShell.Main bg="blue.9">
            <Container
              size={1280}
              pt={{ base: 0, sm: 60 }}
              pb={60}
              px={{ base: 12, sm: 0 }}
            >
              {children}
              {modal}
            </Container>
          </AppShell.Main>
        </AppShell>
      </MantineProvider>
    </QueryProvider>
  );
}
