import { Badge, BadgeProps } from '@mantine/core';
import { motion } from 'framer-motion';
import React from 'react';
import { useMantineTheme } from '@mantine/core';
import { TextSmBold } from '../typography/TextVariants';
import brut from '@/styles/brutalist.module.css';

// Create a motion-capable wrapper to avoid polymorphic component type conflicts.
const BadgeBase = React.forwardRef<HTMLDivElement, BadgeProps>((props, ref) => (
  <Badge ref={ref} {...props} />
));
BadgeBase.displayName = 'BadgeBase';

const MotionBadge = motion.create(BadgeBase);

export function LiveIndicator() {
  // 2. Get access to the Mantine theme to use theme colors.
  const theme = useMantineTheme();

  return (
    <MotionBadge
      variant="filled"
      className={brut.livePill}
      // 3. Apply the 'animate' prop directly to our motion-aware Badge.
      // We are now animating the backgroundColor property.
      animate={{
        backgroundColor: [
            theme.colors.red[3],
            theme.colors.red[4],
            theme.colors.red[3],
        ],
        boxShadow: [
            `0 0 8px 0px ${theme.colors.red[3]}`,
            `0 0 16px 4px ${theme.colors.red[4]}`,
            `0 0 8px 0px ${theme.colors.red[3]}`,
        ],
      }}
      // 4. The transition prop works exactly the same.
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      <TextSmBold c='white'>Live</TextSmBold>
    </MotionBadge>
  );
}
