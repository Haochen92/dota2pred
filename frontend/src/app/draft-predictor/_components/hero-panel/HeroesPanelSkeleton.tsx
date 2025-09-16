'use client';

import { SimpleGrid, Stack, Skeleton } from '@mantine/core';
import HeroCategoryTitle from './HeroCategoryTitle';
import type { AttributeTypes } from './HeroCategoryTitle';

// Skeleton for a single hero category container
function HeroCategorySkeleton({ attribute }: { attribute: AttributeTypes }) {
  return (
    <Stack w='100%' h='100%' align='flex-start' justify='flex-start' gap={16}>
      <HeroCategoryTitle attribute={attribute} />
      <SimpleGrid cols={7} spacing={8} h='auto' w='100%'>
        {Array.from({ length: 35 }).map((_, i) => (
          <Skeleton key={i} height={55} width={80} radius='md' />
        ))}
      </SimpleGrid>
    </Stack>
  );
}

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
