'use client';

import { SimpleGrid } from '@mantine/core';
import HeroCategorySkeleton from './HeroCategorySkeleton';

/**
 * Skeleton placeholder for the full heroes panel.
 * Renders loading placeholders for all hero attribute categories.
 */
export default function HeroesPanelSkeleton() {
  return (
    <SimpleGrid
      cols={{ base: 2, sm: 1, lg: 2 }}
      spacing='24'
      w='100%'
      h='auto'
      p={20}
      bg='gray.9'
      style={{ borderRadius: '24px' }}
      aria-label='Hero panel loading'
    >
  <HeroCategorySkeleton attribute='strength' />
  <HeroCategorySkeleton attribute='intelligence' />
  <HeroCategorySkeleton attribute='agility' />
  <HeroCategorySkeleton attribute='universal' />
    </SimpleGrid>
  );
}
