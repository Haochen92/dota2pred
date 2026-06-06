'use client';

import { Group, Title } from '@mantine/core';
import { TextSmMedium } from '@/components/typography/TextVariants';

export default function DraftHeader() {
  return (
    <Group justify="space-between" align="center" wrap="nowrap">
      {/* Matches Match Tracker's heading: white Title (order 4), Apercu font */}
      <Title order={4} c="white">Draft Predictor</Title>
      <TextSmMedium c="gray.4" visibleFrom="sm" tt="uppercase" style={{ letterSpacing: 1 }}>
        Pick 5 v 5 · predict the winner
      </TextSmMedium>
    </Group>
  );
}
