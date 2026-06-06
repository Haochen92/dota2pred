import { Group, Box, Stack, Title } from '@mantine/core';
import { TextMdBold, TextSmMedium, TextLgBold } from '@/components/typography/TextVariants';
import brut from '@/styles/brutalist.module.css';

interface StatCardProps {
  metric: string;
  color: string;
  average: number;
  max: number;
  secondaryLabel?: string; // defaults to 'Peak'
}

// Helper to format numbers as percentages
const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

export function StatCard({ metric, color, average, max, secondaryLabel = 'Peak' }: StatCardProps) {
  return (
    <Box className={brut.statCard} p="md">
      <Stack gap="sm">
        <Group gap="xs" align="center">
          {/* Color swatch that matches the chart line */}
          <Box className={brut.statSwatch} bg={color} />
          <TextMdBold c="white" tt="uppercase" style={{ letterSpacing: 0.5 }}>
            {metric}
          </TextMdBold>
        </Group>
        <Group grow align="flex-end">
          <Stack gap={0} align="center">
            <Title order={4} c="white">
              {formatPercent(average)}
            </Title>
            <TextSmMedium c="gray.3" tt="uppercase" style={{ letterSpacing: 0.5 }}>
              Average
            </TextSmMedium>
          </Stack>
          <Stack gap={0} align="center">
            <TextLgBold c="blue.3">{formatPercent(max)}</TextLgBold>
            <TextSmMedium c="gray.3" tt="uppercase" style={{ letterSpacing: 0.5 }}>
              {secondaryLabel}
            </TextSmMedium>
          </Stack>
        </Group>
      </Stack>
    </Box>
  );
}
