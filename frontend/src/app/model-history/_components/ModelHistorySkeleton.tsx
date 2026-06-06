'use client';

import { Paper, Stack, Group, Skeleton, SimpleGrid, Box } from '@mantine/core';
import brut from '@/styles/brutalist.module.css';

// Skeleton loader mirroring the layout of ModelHistoryClient while data is fetched via Suspense.
export default function ModelHistorySkeleton() {
  return (
    <Paper
      p="xl"
      component={Stack}
      w="100%"
      h="auto"
      bg="gray.8"
      gap="xl"
      className={brut.panel}
      aria-label="Model history loading"
    >
      {/* Top controls (SegmentedControl placeholder) */}
      <Group justify="space-between" align="center" px={8} w="100%">
        <Skeleton height={36} width={340} radius={10} />
      </Group>

      {/* Chart + Metric selector area */}
      <Group align="flex-start" w="100%" wrap="nowrap" gap="lg">
        {/* Chart placeholder */}
        <Box style={{ flex: 3, width: '100%' }}>
          <Skeleton height={400} radius="md" />
        </Box>
        {/* Chip list placeholder */}
        <Stack gap={8} align="stretch" style={{ width: 120 }}>
          {['accuracy', 'auc', 'root_brier'].map((m) => (
            <Skeleton key={m} height={28} width={100} radius="sm" />
          ))}
        </Stack>
      </Group>

      {/* Stat cards grid */}
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" px={8} w="100%">
        {[0, 1, 2].map((i) => (
          <Box key={i} p="md" className={brut.statCard}>
            <Stack gap={10}>
              <Skeleton height={14} width="40%" />
              <Skeleton height={34} width="70%" />
              <Skeleton height={10} width="55%" />
            </Stack>
          </Box>
        ))}
      </SimpleGrid>
    </Paper>
  );
}
