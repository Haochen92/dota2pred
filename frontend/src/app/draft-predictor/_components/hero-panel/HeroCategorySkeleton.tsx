import { SimpleGrid, Stack, Skeleton } from '@mantine/core';
import HeroCategoryTitle from './HeroCategoryTitle';
import type { HeroCategoryTitleProps } from './HeroCategoryTitle';

/**
 * Skeleton placeholder for a single hero category list.
 * Mirrors the desktop and mobile layouts used by `HerosContainer`.
 */
export default function HeroCategorySkeleton({ attribute }: HeroCategoryTitleProps) {
  return (
    <>
      <Stack
        w='100%'
        h='100%'
        align='flex-start'
        justify='flex-start'
        gap={16}
        visibleFrom='sm'
      >
        {/* Desktop View, visibleFrom='sm' */}
        <HeroCategoryTitle attribute={attribute} />
        <SimpleGrid cols={7} spacing={8} h='auto'>
          {Array.from({ length: 35 }).map((_, i) => (
            <Skeleton key={i} height={55} width={80} radius='md' />
          ))}
        </SimpleGrid>
      </Stack>
      <Stack
        w='100%'
        h='100%'
        align='flex-start'
        justify='flex-start'
        gap={16}
        hiddenFrom='sm'
      >
        {/* Mobile View, hidden on breakpoint > sm */}
        <HeroCategoryTitle attribute={attribute} />
        <SimpleGrid cols={5} spacing={4} h='auto'>
          {Array.from({ length: 35 }).map((_, i) => (
            <Skeleton key={i} height={45} width={70} radius='md' />
          ))}
        </SimpleGrid>
      </Stack>
    </>
  );
}
