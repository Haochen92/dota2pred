import { Group, Stack, Paper, Divider, Center, alpha, Badge, Flex, Box, Collapse, Button } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import Image from 'next/image';

import { IconChevronCompactUp, IconChevronCompactDown } from '@tabler/icons-react';
import TeamDisplayCard from './TeamDisplayCard';
import { TextLgRegular, TextMdRegular, TextSmRegular, TextMdBold, TextLgBold, TextSmBold } from '@/components/typography/TextVariants';
import type { TableRowDataProps } from '@/types/domain';
import { LiveIndicator } from '@/components/motion/LiveIndicator';
import PredictionDetailsClient from '@/components/prediction-details/PredictionDetailsClient';




export default function TableCardView({
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

    const [isOpen, { toggle: toggleOpen }] = useDisclosure(false);

    const TournamentHeader = () => (
                <Group justify='flex-start' align='center' p='md' wrap='nowrap' bg='blue.9'>
                    <Image src='/dota-2.svg' alt="Dota2 Logo" width={16} height={16}/>
                    <TextSmBold ta='center' lineClamp={1}>{tournamentName}</TextSmBold>
                </Group>
    );

    const TimeMatchOutcomeBar = () => (
        <Group justify="space-around" wrap="nowrap" p='12 24 12 24' align="center" bg='blue.9'>
            <Group gap={16} align="center" flex={1} justify="flex-start">
                <TextLgBold>{formattedTime}</TextLgBold>
                <TextMdBold c='gray.2'>{formattedDate}</TextMdBold>
            </Group>
            <Group>
                {
                    actualWinner === null ?
                        <LiveIndicator />
                        : <Badge variant='filled' p='sm' bg={actualWinner === 'Radiant' ? 'green.4' : 'red.4'} c='white'>
                            <TextSmBold>
                                {
                                    actualWinner === 'Radiant' ? 'Radiant Win' : 'Dire Win'
                                }
                            </TextSmBold>
                        </Badge>

                }
            </Group>
        </Group>
    )

    const TeamSection = () => (
        <Stack align="center" p='md' gap={12}>
            <Stack align='flex-start'>
                <TeamDisplayCard teamName={radiantTeamName} heroPicks={radiantHeroes} faction='Radiant' />
            </Stack>

            <Stack align='flex-start'>
                <TeamDisplayCard teamName={direTeamName} heroPicks={direHeroes} faction='Dire' />
            </Stack>
        </Stack>
    )

    const CollapseSection = () => (
            <Stack gap={0} p={0} bg='blue.9'>
                <Group wrap='nowrap' p='md' justify='space-between'>
                    <TextLgBold>View Prediction</TextLgBold>
                    <Group justify='flex-end'>
                        <Button variant='subtle' fullWidth onClick={toggleOpen} c='white'>
                            {isOpen ? <IconChevronCompactUp /> : <IconChevronCompactDown />}
                        </Button>
                    </Group>
                </Group>
                <Collapse in={isOpen} px='xs'>
                    <PredictionDetailsClient matchId={matchId} mode='mobile' />
                </Collapse>
            </Stack>
    )


    return (
        <Paper shadow="xl" radius="md" withBorder hiddenFrom={visibilityBreakpoint} maw='90vw' style={{overflow: 'hidden'}} bg='gray.7'>
            <Stack gap={0} align='stretch'>
                <TournamentHeader/>
                <TimeMatchOutcomeBar />

                {/* Main Content: Teams Facing Off */}

                <TeamSection />
                <CollapseSection />
                {/*  */}
            </Stack>
        </Paper>
    );
}
