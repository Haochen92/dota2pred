'use client';
import { Suspense } from 'react';
import { Stack } from '@mantine/core';

import HeroesPanel from './hero-panel/HeroesPanel';
import DraftingPanel from './draft-panel/DraftingPanel';
import HeroesPanelSkeleton from './hero-panel/HeroesPanelSkeleton';
import PredictionPanel from '../prediction-panel/PredictionPanel';
import DraftHeader from './DraftHeader';
import { DraftProvider } from '@/context/DraftContext';

export default function DraftPredictorClient() {
  return (
    <DraftProvider>
      {/* Single responsive tree — child panels handle their own sm breakpoints */}
      <Stack w="100%" c="white" gap={24} py={{ base: 8, sm: 0 }}>
        <DraftHeader />
        <DraftingPanel />
        <PredictionPanel />
        <Suspense fallback={<HeroesPanelSkeleton />}>
          <HeroesPanel />
        </Suspense>
      </Stack>
    </DraftProvider>
  );
}
