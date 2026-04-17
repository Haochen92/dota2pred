import Image from 'next/image';
import { Box } from '@mantine/core';

export type IconProps = {
  size?: number;
  alt?: string;
};

export function StarIcon({ size = 16, alt = 'star icon' }: IconProps) {
  return (
    <Box w={size} h={size} pos="relative" style={{ flex: '0 0 auto' }}>
      <Image src="/icons/stars/star.svg" alt={alt} fill sizes={`${size}px`} />
    </Box>
  );
}

export function StarMultiIcon({ size = 16, alt = 'multi star icon' }: IconProps) {
  return (
    <Box w={size} h={size} pos="relative" style={{ flex: '0 0 auto' }}>
      <Image src="/icons/stars/star-multi.svg" alt={alt} fill sizes={`${size}px`} />
    </Box>
  );
}

export function AiIcon({ size = 16, alt = 'ai icon' }: IconProps) {
  return (
    <Box w={size} h={size} pos="relative" style={{ flex: '0 0 auto' }}>
      <Image src="/icons/stars/ai-icon.svg" alt={alt} fill sizes={`${size}px`} />
    </Box>
  );
}
