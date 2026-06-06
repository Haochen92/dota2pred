'use client';

import { Box, SimpleGrid } from '@mantine/core';
import HeroCategorySkeleton from './HeroCategorySkeleton';
import classes from '../../draft-predictor.module.css';

/**
 * Skeleton placeholder for the full heroes panel.
 * Mirrors the brutalist HeroesPanel layout.
 */
export default function HeroesPanelSkeleton() {
  return (
    <Box className={classes.panel} p={20} aria-label="Hero panel loading">
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing={28} w="100%">
        <HeroCategorySkeleton attribute="strength" />
        <HeroCategorySkeleton attribute="intelligence" />
        <HeroCategorySkeleton attribute="agility" />
        <HeroCategorySkeleton attribute="universal" />
      </SimpleGrid>
    </Box>
  );
}
