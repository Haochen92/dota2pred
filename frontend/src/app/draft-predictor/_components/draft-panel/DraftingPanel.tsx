'use client';

import { Group, Stack, Title, Flex } from '@mantine/core';

import  useDraftContext  from '@/hooks/useDraftContext';
import DraftSlot from './DraftSlot';
import CompactDraftSlot from './CompactDraftSlot';
import { TextLgBold } from '@/components/typography/TextVariants';

interface TeamPanelProps {
  team: 'RADIANT' | 'DIRE';
}

const TeamPanel = ({ team }: TeamPanelProps) => {

  const draftTeam = team === 'RADIANT' ? 'radiantTeam' : 'direTeam';
  const { form, handleRemoveHero } = useDraftContext();
  const { activeSlot } = form.values;
  const pickedHeroes = form.values[draftTeam];


  return (
    <>
      <Stack flex={1} gap={8} visibleFrom='sm'>
      {/* Desktop only view, hidden from breakpoint <= sm*/}
        <Title order={3} c={team === 'RADIANT' ? 'green.2' : 'red.2'}>{team}</Title>
        <Group h='100%' w='100%' wrap='nowrap' gap={8} p='12 8 12 8' bg='gray.7' justify='flex-start' style={{borderRadius: 12, overflow: 'hidden'}}>
            {Array.from({ length: 5 }).map((_, index) => {
                const heroId = pickedHeroes[index];
                const isActive = activeSlot?.team === draftTeam && activeSlot?.index === index;
                const handleClick = () => {
                    if (heroId !== null) {
                      handleRemoveHero({ team: draftTeam, index });
                    }
                    form.setFieldValue('activeSlot', { team: draftTeam, index });
                }

                return (
                    <DraftSlot
                        key={index}
                        heroId={heroId}
                        isActive={isActive}
                        onClick={handleClick}
                    />
                );
            })}
        </Group>
      </Stack>
      <Stack flex={1} gap={8} hiddenFrom='sm' p={4}>
      {/* Mobile view, hidden on breakpoint > sm*/}
        <TextLgBold c={team === 'RADIANT' ? 'green.2' : 'red.2'}>{team}</TextLgBold>
        <Group h='100%' w='100%' wrap='nowrap' gap={2} p='4 4 4 4' justify='flex-start' style={{borderRadius: 12, overflow: 'hidden'}}>
            {Array.from({ length: 5 }).map((_, index) => {
                const heroId = pickedHeroes[index];
                const isActive = activeSlot?.team === draftTeam && activeSlot?.index === index;
                const handleClick = () => {
                    if (heroId !== null) {
                      handleRemoveHero({ team: draftTeam, index });
                    }
                    form.setFieldValue('activeSlot', { team: draftTeam, index });
                }

                return (
                    <CompactDraftSlot
                        key={index}
                        heroId={heroId}
                        isActive={isActive}
                        onClick={handleClick}
                    />
                );
            })}
        </Group>
      </Stack>
    </>

  )
}

export default function DraftingPanel() {
  return (
    <Flex justify='space-around' align='center' gap='sm' w='100%' direction='row'>
      <TeamPanel team='RADIANT' />
      <TeamPanel team='DIRE' />
    </Flex>
  )
}
