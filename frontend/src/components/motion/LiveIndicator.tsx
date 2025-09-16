import { Badge } from '@mantine/core';
import { motion } from 'framer-motion';
import { useMantineTheme } from '@mantine/core';
import { TextSmBold } from '../typography/TextVariants';

// 1. Create a "motion-aware" version of the Mantine Badge component.
// This new component accepts all Badge props AND all Framer Motion props.
const MotionBadge = motion(Badge);

export function LiveIndicator() {
  // 2. Get access to the Mantine theme to use theme colors.
  const theme = useMantineTheme();

  return (
    <MotionBadge
      variant="filled"
      // 3. Apply the 'animate' prop directly to our motion-aware Badge.
      // We are now animating the backgroundColor property.
      animate={{
        backgroundColor: [
            theme.colors.red[5],
            theme.colors.green[5],
            theme.colors.red[5],
        ],
        boxShadow: [
            `0 0 8px 0px ${theme.colors.red[3]}`,
            `0 0 16px 4px ${theme.colors.green[3]}`,
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
