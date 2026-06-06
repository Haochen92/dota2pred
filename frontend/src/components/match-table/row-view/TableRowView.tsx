'use client';

import { Group, Stack, Flex } from '@mantine/core';
import { StarIcon } from '@/components/icons/StarIcon';
import { IconCircleCheckFilled, IconCircleXFilled} from '@tabler/icons-react';
import TeamDisplay from './TeamDisplay';
import { TextMdRegular, TextSmRegular, TextMdBold } from '@/components/typography/TextVariants';
import type { TableRowDataProps } from '@/types/domain';
import { LiveIndicator } from '@/components/motion/LiveIndicator';
import PredictionDetailsModal from './PredictionDetailsModal';
import brut from '@/styles/brutalist.module.css';

export default function TableRowView({
    matchId,
    tournamentName,
    formattedTime,
    formattedDate,
    radiantTeamName,
    radiantHeroes,
    direTeamName,
    direHeroes,
    predictedWinner,
    actualWinner,
    isCorrectPrediction,
    visibilityBreakpoint
}: TableRowDataProps) {
    return (
        <Group id='tableRow' w='100%' h={80} p={0} gap={0} wrap='nowrap' align="center" justify="flex-start" visibleFrom={visibilityBreakpoint} className={brut.bodyRow}>
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
            <TeamDisplay teamName={radiantTeamName} heroPicks={radiantHeroes} />

            {/* Column 4: Dire Team */}
            <TeamDisplay teamName={direTeamName} heroPicks={direHeroes} />

            {/* Column 5: Prediction */}
            <Group flex={1.5} gap={16} pl={12} pr={12}>
                {predictedWinner === null ? (
                <TextMdBold>No Prediction</TextMdBold>
                ) : (

                    <PredictionDetailsModal match_id={matchId}>
                        <Group wrap="nowrap" gap={4}>
                            <TextMdBold c={predictedWinner === 'Dire' ? 'red.2' : 'green.2'}>
                                {predictedWinner}
                            </TextMdBold>
                            <StarIcon size={16} />
                        </Group>
                    </PredictionDetailsModal>
                )}
            </Group>
            {/* Column 6: Actual Outcome */}
            <Group flex={1.5} gap={16} pl={12} pr={12}>
                <Group gap={4} c={actualWinner === null ? 'white' : (actualWinner === 'Dire' ? 'red.2' : 'green.2')}>
                    {actualWinner === null ? <LiveIndicator/> :
                        <TextMdBold>{actualWinner}</TextMdBold>}
                </Group>
            </Group>

            {/* Column 7: Correct Prediction */}
            <Flex flex={0.5} h='100%' align='center'>
                {isCorrectPrediction !== null && (
                    isCorrectPrediction
                        ? <IconCircleCheckFilled color='var(--mantine-color-blue-4)' size={32} />
                        : <IconCircleXFilled color='var(--mantine-color-gray-4)' size={32} />
                )}
            </Flex>
        </Group>
    );
}
