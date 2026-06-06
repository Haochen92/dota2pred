'use client';

import { Box, Flex, Group, Stack } from '@mantine/core';

import useDraftContext from '@/hooks/useDraftContext';
import DraftSlot from './DraftSlot';
import CompactDraftSlot from './CompactDraftSlot';
import classes from '../../draft-predictor.module.css';

type Team = 'RADIANT' | 'DIRE';

const accentOf = (team: Team) =>
  team === 'RADIANT' ? 'var(--mantine-color-green-4)' : 'var(--mantine-color-red-4)';
const keyOf = (team: Team) => (team === 'RADIANT' ? 'radiantTeam' : 'direTeam');

function TeamHeader({ team }: { team: Team }) {
  const { form } = useDraftContext();
  const count = form.values[keyOf(team)].filter((h) => h !== null).length;
  return (
    <Box className={classes.teamHeader} style={{ '--team-accent': accentOf(team) } as React.CSSProperties}>
      {team}
      <span className={classes.teamCount}>{count}/5</span>
    </Box>
  );
}

function TeamBoard({ team, compact, grow }: { team: Team; compact?: boolean; grow?: boolean }) {
  const draftTeam = keyOf(team);
  const { form, handleRemoveHero } = useDraftContext();
  const { activeSlot } = form.values;
  const picked = form.values[draftTeam];
  const Slot = compact ? CompactDraftSlot : DraftSlot;

  return (
    <Box
      className={classes.board}
      flex={grow ? 1 : undefined}
      miw={grow ? 0 : undefined}
    >
      {Array.from({ length: 5 }).map((_, index) => {
        const heroId = picked[index];
        const isActive = activeSlot?.team === draftTeam && activeSlot?.index === index;
        const handleClick = () => {
          if (heroId !== null) {
            handleRemoveHero({ team: draftTeam, index });
          }
          form.setFieldValue('activeSlot', { team: draftTeam, index });
        };

        return (
          <Slot
            key={`${draftTeam}-slot-${index}`}
            heroId={heroId}
            isActive={isActive}
            onClick={handleClick}
            index={index}
            team={team}
          />
        );
      })}
    </Box>
  );
}

export default function DraftingPanel() {
  return (
    <>
      {/* Desktop: headers in their own row, then the two boards with a
          vertically-centred VS badge sitting between the slot rows. */}
      <Stack visibleFrom="sm" gap={10} w="100%">
        <Group justify="space-between" wrap="nowrap">
          <TeamHeader team="RADIANT" />
          <TeamHeader team="DIRE" />
        </Group>
        <Flex align="center" gap="md" w="100%">
          <TeamBoard team="RADIANT" grow />
          <Box className={classes.vsBadge}>VS</Box>
          <TeamBoard team="DIRE" grow />
        </Flex>
      </Stack>

      {/* Mobile: stacked compact boards */}
      <Stack hiddenFrom="sm" gap={12} w="100%">
        <Stack gap={8} align="flex-start">
          <TeamHeader team="RADIANT" />
          <TeamBoard team="RADIANT" compact />
        </Stack>
        <Stack gap={8} align="flex-start">
          <TeamHeader team="DIRE" />
          <TeamBoard team="DIRE" compact />
        </Stack>
      </Stack>
    </>
  );
}
