'use client';

import { parseISO, format, isToday } from 'date-fns';
import { Group, Stack, Flex } from '@mantine/core';
import type { MatchData } from '@/types/domain';
import { StarIcon } from '@/components/icons/StarIcon';
import { IconCircleCheckFilled, IconCircleXFilled} from '@tabler/icons-react';
import TeamDisplay from './TeamDisplay';
import { extractHeroPicks } from '@/utils/extract-hero-picks';
import { TextMdRegular, TextSmRegular, TextMdBold } from '@/components/typography/TextVariants';

type TableRowProps = {
    matchData: MatchData;
};

export default function TableRow({ matchData }: TableRowProps) {

    const startTime = parseISO(matchData.start_time);
    const tournamentName = matchData.league_data?.name || 'Tournament';

    // Format time to be like "4:32 PM"
    const formattedTime = format(startTime, 'p');
    const formattedDate = isToday(startTime) ? 'Today' : format(startTime, 'MMM dd, yyyy');
    const heroPicks = extractHeroPicks(matchData);

    // predicted_outcome: true for Radiant, false for Dire
    const isPredicted = matchData.predicted_outcome !== null;
    const predictedWinner = isPredicted ? ( matchData.predicted_outcome === false ? 'Dire' : 'Radiant' ): null;

    const isCompleted = 'radiant_win' in matchData;
    const actualWinner = isCompleted ? (matchData.radiant_win ? 'Radiant' : 'Dire') : null;
    const correctPrediction = isCompleted && isPredicted ? predictedWinner === actualWinner : null;

    return (
        <Group id='tableRow' w='100%' h={80} p={0} gap={0} wrap='nowrap' align="center" justify="flex-start" style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}>
            {/* Column 1: Time & Date */}
            <Stack w={120} h='100%' gap={16} px={12} justify='center'>
                <Stack gap={0}>
                    <TextMdRegular>{formattedTime}</TextMdRegular>
                    <TextSmRegular c='gray.2'>{formattedDate}</TextSmRegular>
                </Stack>
            </Stack>

            {/* Column 2: League */}
            <Group flex={1.5} pl={12} pr={12} h='100%' gap={16}>
                <TextMdRegular>{tournamentName}</TextMdRegular>
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
            <Group flex={1.5} gap={16} pl={12} pr={12} pt={0} pb={0}>
                <Group wrap='nowrap' gap={4}>
                    {predictedWinner === null ? <TextMdBold c='white'> No Prediction </TextMdBold> :
                        <TextMdBold c={predictedWinner === 'Dire' ? 'red.2' : 'green.2'}>{predictedWinner}</TextMdBold>}
                    <StarIcon size={16} />
                </Group>
            </Group>

            {/* Column 6: Actual Outcome */}
            <Group flex={1.5} gap={16} pl={12} pr={12}>
                <Group gap={4} c={actualWinner === null ? 'white' : ( actualWinner === 'Dire' ? 'red.2' : 'green.2' )}>
                    {
                        actualWinner === null ? <TextMdBold> Match in Progress</TextMdBold> :
                         <TextMdBold>{actualWinner}</TextMdBold>
                    }
                </Group>
            </Group>

            {/* Column 7: Correct Prediction */}
            <Flex flex={0.5} h='100%' align='center'>
                {correctPrediction !== null &&  (
                    correctPrediction
                        ? <IconCircleCheckFilled color='var(--mantine-color-blue-4)' size={32}/>
                        : <IconCircleXFilled color='var(--mantine-color-gray-4)' size={32}/>
                )}
            </Flex>
        </Group>
    )
}
