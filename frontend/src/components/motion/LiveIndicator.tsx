import { Badge } from '@mantine/core';
import React from 'react';
import { TextSmBold } from '../typography/TextVariants';
import brut from '@/styles/brutalist.module.css';
import classes from './LiveIndicator.module.css';

export function LiveIndicator() {
  return (
    <Badge
      variant="filled"
      className={`${brut.livePill} ${classes.livePulse}`}
    >
      <TextSmBold c='white'>Live</TextSmBold>
    </Badge>
  );
}
