'use client';

import React from 'react';
import { Paper, Title, Text, Button } from '@mantine/core';

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Paper p="xl" withBorder>
          <Title order={3}>Something went wrong</Title>
          <Text c="red">{this.state.error?.message}</Text>
          <Button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </Button>
        </Paper>
      );
    }

    return this.props.children;
  }
}
