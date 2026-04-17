'use client';
import { Suspense } from 'react';
import { Stack, Title, useMantineTheme } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';

import HeroesPanel from './hero-panel/HeroesPanel';
import DraftingPanel from './draft-panel/DraftingPanel';
import HeroesPanelSkeleton from './hero-panel/HeroesPanelSkeleton';
import PredictionPanel from '../prediction-panel/PredictionPanel';
import { DraftProvider } from '@/context/DraftContext';

export default function DraftPredictorClient() {
  const theme = useMantineTheme();
  const desktopBreakpoint = theme.breakpoints.sm;
  const isDesktop = useMediaQuery(`(min-width: ${desktopBreakpoint})`);

  const DesktopComponent = () => (
      <Stack w='100%' c='white' gap={60} justify='center' visibleFrom='sm'>
        {/* Desktop only view, hidden from breakpoint <= sm*/}
        <Title order={5} mb='md'>Draft Predictor</Title>
        <DraftingPanel/>
        <PredictionPanel />
        <Suspense fallback={<HeroesPanelSkeleton />}>
          <HeroesPanel />
        </Suspense>
      </Stack>
  );

  const MobileComponent = () => (
    <Stack w='100%' c='white' gap={12} justify='space-between' hiddenFrom='sm'>
        {/* Mobile only view, hidden on breakpoint > sm*/}
        <Title order={6} m='md'>Draft Predictor</Title>
        <DraftingPanel/>
        <Suspense fallback={<HeroesPanelSkeleton />}>
          <HeroesPanel />
        </Suspense>
        <PredictionPanel />
      </Stack>
  )

  return (
    <DraftProvider>
      {
        isDesktop ? <DesktopComponent /> : <MobileComponent />
      }
    </DraftProvider>
  );
}
