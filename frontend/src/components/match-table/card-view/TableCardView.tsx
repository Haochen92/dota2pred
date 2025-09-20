import { Group, Stack, Paper, Divider, Center, alpha, Badge, Flex, Box } from '@mantine/core';
import { StarIcon } from '@/components/icons/StarIcon';
import { IconCircleCheckFilled, IconCircleXFilled} from '@tabler/icons-react';
import TeamDisplayCard from './TeamDisplayCard';
import { TextMdRegular, TextSmRegular, TextMdBold, TextLgRegular, TextLgBold } from '@/components/typography/TextVariants';
import type { TableRowDataProps } from '@/types/domain';
import { LiveIndicator } from '@/components/motion/LiveIndicator';
import { IconSwords } from '@tabler/icons-react';




export default function TableCardView({
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
        <Paper shadow="xl" radius="md" withBorder hiddenFrom={visibilityBreakpoint}
            style={(theme) => ({
                overflow:'hidden',
                background: alpha(theme.colors.gray[4], 0.2),
                backdropFilter: 'blur(16px)',
                border: `1px solid ${alpha(theme.colors.gray[4], 0.2)}`,
                backgroundImage: `radial-gradient(circle at top left, ${alpha(theme.colors.gray[2], 0.15)}, transparent 50%)`,
            })}
            maw='90vw'
        >
            <Stack gap={4} align='stretch'>
                {/* Card Header: Tournament & Time */}
                <Group justify='center' align='center' p='md'>
                    <TextLgBold ta='center'>{tournamentName}</TextLgBold>
                </Group>
                <Group justify="space-around" wrap="nowrap" p='4 24 4 24' align="center">
                    <Group gap={16} align="center" flex={1} justify="start">
                        <TextLgRegular>{formattedTime}</TextLgRegular>
                        <TextMdRegular c='gray.2'>{formattedDate}</TextMdRegular>
                    </Group>
                    <Group>
                        {
                            actualWinner === null ?
                                <LiveIndicator />
                             : <Badge variant='filled' p='sm' bg='white' c='black'>
                                    <TextSmRegular>
                                        Completed
                                    </TextSmRegular>
                                </Badge>

                        }
                    </Group>
                </Group>

                <Divider w='95%' />

                {/* Main Content: Teams Facing Off */}
                <Stack align="center" p='md' gap={12}>
                    <Stack align='flex-start'>
                        <TeamDisplayCard teamName={radiantTeamName} heroPicks={radiantHeroes} faction='Radiant' />
                    </Stack>

                    <IconSwords size={32} fill='var(--mantine-color-red-2)' />

                    <Stack align='flex-start'>
                        <TeamDisplayCard teamName={direTeamName} heroPicks={direHeroes} faction='Dire' />
                    </Stack>
                </Stack>

                <Divider w='95%' />

                {/*  */}
                <Stack gap={16} p={12}>
                    <Group justify="center" gap={16} wrap="nowrap" w='100%'>
                        {/* Prediction Box */}
                        <Box
                            style={(theme)=>({
                                flex: 1,
                                border: `1px solid ${alpha(theme.colors.gray[4],0.35)}`,
                                background: alpha(theme.colors.gray[6] ?? theme.black, 0.25),
                                borderRadius: 12,
                                padding: '16px 24px',
                                Width: '40%'
                            })}
                        >
                            <Stack gap={8}>
                                <TextSmRegular style={{letterSpacing:1}} c="gray.2">PREDICTION</TextSmRegular>
                                <Group gap={8} wrap="nowrap">
                                    {/* Status Icon */}
                                    <Center
                                        w={28}
                                        h={28}
                                        style={(theme)=>({
                                            borderRadius: '50%',
                                            background: predictedWinner && (actualWinner && isCorrectPrediction !== null) ?
                                                (isCorrectPrediction ? theme.colors.green[6] : theme.colors.red[6]) : alpha(theme.colors.gray[4],0.35),
                                            color: '#fff'
                                        })}
                                    >
                                        {predictedWinner ? (
                                            actualWinner && isCorrectPrediction !== null ? (
                                                isCorrectPrediction ? <IconCircleCheckFilled size={18} /> : <IconCircleXFilled size={18} />
                                            ) : <StarIcon size={16} />
                                        ) : null}
                                    </Center>
                                    {predictedWinner === null ? (
                                        <TextMdBold>No Prediction</TextMdBold>
                                    ) : (
                                        <TextMdBold>{predictedWinner}</TextMdBold>
                                    )}
                                </Group>
                            </Stack>
                        </Box>

                        {/* Outcome Box */}
                        <Box
                            style={(theme)=>({
                                flex: 1,
                                border: `1px solid ${alpha(theme.colors.gray[4],0.35)}`,
                                background: alpha(theme.colors.gray[6] ?? theme.black, 0.25),
                                borderRadius: 12,
                                padding: '16px 24px',
                                width: '40%'
                            })}
                        >
                            <Stack gap={8}>
                                <TextSmRegular style={{letterSpacing:1}} c="gray.2">OUTCOME</TextSmRegular>
                                <Group gap={8} wrap="nowrap">
                                    <Center
                                        w={28}
                                        h={28}
                                        style={(theme)=>({
                                            borderRadius: '50%',
                                            background: actualWinner ? theme.colors.green[6] : alpha(theme.colors.gray[4],0.35),
                                            color: '#fff'
                                        })}
                                    >
                                        {actualWinner ? <IconCircleCheckFilled size={18} /> : <LiveIndicator />}
                                    </Center>
                                    {actualWinner === null ? (
                                        <TextMdBold c="gray.2">Ongoing</TextMdBold>
                                    ) : (
                                        <TextMdBold>{actualWinner}</TextMdBold>
                                    )}
                                </Group>
                            </Stack>
                        </Box>
                    </Group>

                    {/* Prediction Banner */}
                    {isCorrectPrediction !== null && predictedWinner !== null && actualWinner !== null && (
                        <Box
                            style={(theme)=>({
                                width: '100%',
                                background: isCorrectPrediction
                                    ? `linear-gradient(90deg, ${theme.colors.green[5]} 0%, ${theme.colors.teal[5]} 100%)`
                                    : `linear-gradient(90deg, ${theme.colors.red[6]} 0%, ${theme.colors.orange[6]} 100%)`,
                                padding: '16px 32px',
                                borderRadius: 999,
                                boxShadow: `0 4px 24px -4px ${alpha(isCorrectPrediction ? theme.colors.green[6] : theme.colors.red[6],0.45)}`,
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center'
                            })}
                        >
                            <Group>
                                {isCorrectPrediction
                                    ? <IconCircleCheckFilled color='var(--mantine-color-white)' size={24} />
                                    : <IconCircleXFilled color='var(--mantine-color-red-2)' size={24} />
                                }
                                <TextMdBold style={{display:'flex',alignItems:'center',gap:8}}>
                                    {isCorrectPrediction ? ' Prediction Correct' : ' Prediction Incorrect'}
                                </TextMdBold>
                            </Group>

                        </Box>
                    )}
                </Stack>
            </Stack>
        </Paper>
    );
}
