import React, { useState } from 'react';
import { Group, Stack, Paper, Badge, Box, Collapse, Button } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import Image from 'next/image';

import { IconChevronDown, IconChevronUp } from '@tabler/icons-react';
import TeamDisplayCard from './TeamDisplayCard';
import { TextMdBold, TextLgBold, TextSmBold } from '@/components/typography/TextVariants';
import type { TableRowDataProps } from '@/types/domain';
import { LiveIndicator } from '@/components/motion/LiveIndicator';
import PredictionDetailsClient from '@/components/prediction-details/PredictionDetailsClient';
import brut from '@/styles/brutalist.module.css';

const HARD_DIVIDER = '2px solid var(--mantine-color-gray-6)';

function TableCardView({
    matchId,
    tournamentName,
    formattedTime,
    formattedDate,
    radiantTeamName,
    radiantHeroes,
    direTeamName,
    direHeroes,
    actualWinner,
    visibilityBreakpoint,
}: TableRowDataProps) {
    const [isOpen, { toggle: toggleOpen }] = useDisclosure(false);
    // Lazy-mount latch: defer the prediction fetch + chart until first open,
    // then keep it mounted so collapse animations stay smooth and SWR caches.
    const [hasOpened, setHasOpened] = useState(false);
    const handleToggle = () => {
        setHasOpened(true);
        toggleOpen();
    };

    return (
        <Paper
            hiddenFrom={visibilityBreakpoint}
            maw="90vw"
            w="100%"
            bg="gray.8"
            className={brut.panel}
            style={{ overflow: 'hidden' }}
        >
            <Stack gap={0} align="stretch">
                {/* Tournament header */}
                <Group gap={8} p="10 14" wrap="nowrap" bg="gray.9" style={{ borderBottom: HARD_DIVIDER }}>
                    <Image src="/dota-2.svg" alt="Dota2 Logo" width={16} height={16} />
                    <TextSmBold tt="uppercase" lineClamp={1} style={{ letterSpacing: 0.5 }}>
                        {tournamentName}
                    </TextSmBold>
                </Group>

                {/* Time + outcome */}
                <Group justify="space-between" wrap="nowrap" p="12 14" align="center">
                    <Group gap={10} align="baseline" wrap="nowrap">
                        <TextLgBold>{formattedTime}</TextLgBold>
                        <TextMdBold c="gray.3">{formattedDate}</TextMdBold>
                    </Group>
                    {actualWinner === null ? (
                        <LiveIndicator />
                    ) : (
                        <Badge
                            className={brut.badge}
                            variant="filled"
                            p="sm"
                            bg={actualWinner === 'Radiant' ? 'green.4' : 'red.4'}
                            c="white"
                        >
                            {actualWinner === 'Radiant' ? 'Radiant Win' : 'Dire Win'}
                        </Badge>
                    )}
                </Group>

                {/* Teams */}
                <Stack gap={12} px={14} pb={14}>
                    <TeamDisplayCard teamName={radiantTeamName} heroPicks={radiantHeroes} faction="Radiant" />
                    <TeamDisplayCard teamName={direTeamName} heroPicks={direHeroes} faction="Dire" />
                </Stack>

                {/* View prediction */}
                <Box p={12} bg="gray.9" style={{ borderTop: HARD_DIVIDER }}>
                    <Button
                        className={brut.btn}
                        bg="gray.7"
                        c="gray.1"
                        radius={8}
                        fullWidth
                        onClick={handleToggle}
                        rightSection={isOpen ? <IconChevronUp size={18} /> : <IconChevronDown size={18} />}
                    >
                        View Prediction
                    </Button>
                    <Collapse in={isOpen} px="xs">
                        {hasOpened && <PredictionDetailsClient matchId={matchId} mode="mobile" />}
                    </Collapse>
                </Box>
            </Stack>
        </Paper>
    );
}

export default React.memo(TableCardView);
