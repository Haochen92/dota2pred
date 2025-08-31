'use client';

import { parseISO, format, isToday } from 'date-fns';
import { Group, Stack, Flex, Text } from '@mantine/core';
import { LiveMatchData } from '@/types/contracts/index';
import { StarIcon } from '@/components/icons/StarIcon';
import { IconCircleCheckFilled, IconCircleXFilled } from '@tabler/icons-react';
import TeamDisplay from './TeamDisplay';
import { extractHeroPicks } from '@/utils/extract-hero-picks';
import { TextMdRegular, TextSmRegular, TextMdBold } from '@/components/typography/TextVariants';

type TableRowProps = {
    matchData: LiveMatchData;
};

export default function TableRow({ matchData }: TableRowProps) {
    const startTime = parseISO(matchData.start_time);
    
    // Format time to be like "4:32 PM"
    const formattedTime = format(startTime, 'p'); 
    const formattedDate = isToday(startTime) ? 'Today' : format(startTime, 'MMM dd, yyyy');
    const heroPicks = extractHeroPicks(matchData);

    // Assuming predicted_outcome: true for Radiant, false for Dire
    const predictedWinner = matchData.predicted_outcome === false ? 'Dire' : 'Radiant';
    const correctPrediction = true

    return (
        <Group w='100%' h={80} p={0} gap={0} wrap='nowrap' align="center" justify="flex-start" style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}>
            {/* Column 1: Time & Date */}
            <Stack w={120} h='100%' gap={14} pl={12} pr={12} justify='center'>
                <Stack gap={0}>
                    <TextMdRegular>{formattedTime}</TextMdRegular>
                    <TextSmRegular c='gray.2'>{formattedDate}</TextSmRegular>
                </Stack>
            </Stack>

            {/* Column 2: League */}
            <Group flex={1.5} pl={12} pr={12} h='100%' gap={16}>
                <TextMdRegular>{matchData.leagueid ? `League ${matchData.leagueid}` : 'Tournament'}</TextMdRegular>
            </Group>

            {/* Column 3: Radiant Team */}
            <TeamDisplay 
                teamName={matchData.radiant_name || ''}
                heroPicks={heroPicks.radiant}
            />

            {/* Column 4: Dire Team */}
            <TeamDisplay  
                teamName={matchData.dire_name || ''}
                heroPicks={heroPicks.dire}
            />

            {/* Column 5: Prediction */}
            <Group flex={1.5} gap={16} pl={12} pr={12}>
                <Group wrap='nowrap' gap={4} c={predictedWinner === 'Dire' ? 'red.2' : 'green.2'}>
                    <TextMdBold>{predictedWinner}</TextMdBold>
                    <StarIcon size={16} />
                </Group>
            </Group>

            {/* Column 6: Actual Outcome */}
            <Group flex={1.5} gap={16} pl={12} pr={12}>
                <Group gap={4} c={predictedWinner === 'Dire' ? 'red.2' : 'green.2'}>
                    {
                        predictedWinner ? <TextMdBold>{predictedWinner}</TextMdBold> : <TextMdBold c='white'> Match in Progress</TextMdBold>
                    }
                </Group>
            </Group>

            {/* Column 7: Correct  */}
            <Flex flex={0.5} h='100%' align='center'>
                {correctPrediction ? <IconCircleCheckFilled color='var(--mantine-color-blue-4)' size={32}/> : null}
            </Flex>
        </Group>
    )
}