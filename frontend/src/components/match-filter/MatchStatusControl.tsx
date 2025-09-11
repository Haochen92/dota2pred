'use client';

import { SegmentedControl, Flex } from '@mantine/core';
import type { MatchFilterOptions, MatchStatus } from '@/types/domain';
import { TextMdBold } from '../typography/TextVariants';

type MatchStatusControlProps = {
  filters: MatchFilterOptions;
  onFilterChange: (filters: MatchFilterOptions) => void;
};

const ControlTab = (label: string) => {
    return (
        <Flex justify='center' align='center'
            style={{borderRadius: 6, padding: '8px 24px', gap:'6px'}}
        >
            <TextMdBold c='gray.2'>{label}</TextMdBold>
        </Flex>
    )
}

export function MatchStatusControl({ filters, onFilterChange }: MatchStatusControlProps) {
  const value = filters.matchStatus ?? 'All';

  const dataProps = [
    { label: ControlTab('All'), value: 'All' },
    { label: ControlTab('Live'), value: 'Live' },
    { label: ControlTab('Past'), value: 'Completed' },
  ];

  const handleStatusChange = (val: string) => {
    if (val === 'All') {
      onFilterChange({
        ...filters,
        matchStatus: undefined,
      });
      return;
    }
    onFilterChange({
      ...filters,
      matchStatus: val as MatchStatus,
    });
  };

  return (
    <SegmentedControl
        value={value}
        onChange={handleStatusChange}
        data={dataProps}

        p={4}
        bg='gray.7'
        radius={10}
        styles={(theme) => ({
            indicator: {
                backgroundColor: theme.colors.gray[9],
            },
            root: {
                gap: theme.spacing.xs,
            },
        })}
        withItemsBorders={false}
        transitionDuration={150}
        transitionTimingFunction='linear'
    />
  );
}
