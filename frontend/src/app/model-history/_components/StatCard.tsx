import { Paper, Text, Group, Box, Stack, Title } from '@mantine/core';
import { TextMdRegular, TextSmMedium, TextLgBold } from '@/components/typography/TextVariants';

interface StatCardProps {
  metric: string;
  color: string;
  average: number;
  max: number;
}

// Helper to format numbers as percentages
const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

export function StatCard({ metric, color, average, max }: StatCardProps) {
  return (
    <Paper radius="md" p="sm" bg="gray.8">
      <Stack gap="xs">
        <Group justify="space-between" align="center">
          <Group gap="xs" align="center">
            {/* Color indicator that matches the chart line */}
            <Box w={12} h={20} bg={color} style={{ borderRadius: 8 }} />
            <TextMdRegular c="white" tt="capitalize">{metric}</TextMdRegular>
          </Group>
        </Group>
        <Group grow align="flex-end">
            <Stack gap={0} align="center">
                <Title order={6} c="white">
                    {formatPercent(average)}
                </Title>
                <TextMdRegular c="gray.1" >Average</TextMdRegular>
            </Stack>
            <Stack gap={0} align="center">
                <TextLgBold c="gray.1">
                    {formatPercent(max)}
                </TextLgBold>
                <TextMdRegular c="gray.2" >Peak</TextMdRegular>
            </Stack>
        </Group>
      </Stack>
    </Paper>
  );
}
