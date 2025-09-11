'use client';
import { useState } from 'react';

import { Stack, Title } from '@mantine/core';
import HeroesPanel from './_components/HeroesPanel';

export default function DraftPredictorClient() {
  return (
      <Stack w='100%' c="white" gap={60} justify='center'>
          <Title order={5} mb="md">Draft Predictor</Title>
          <HeroesPanel />
      </Stack>
  )
}
