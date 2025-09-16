import { Group, Stack, alpha, getGradient } from '@mantine/core';
import HeroIcon from '@/components/icons/HeroIcon';
import { TextLgRegular, TextLgBold } from '@/components/typography/TextVariants';

type TeamDisplayProps = {
    teamName: string;
    heroPicks: number[];
    faction: 'Radiant' | 'Dire';
};

export default function TeamDisplayCard({ teamName, heroPicks, faction }: TeamDisplayProps) {
    const isRadiant = faction === 'Radiant';

    return (
        <Stack
            align="flex-start"
            justify="center"
            gap={4}
            flex={2.5}
            h='100%'
            pt={8}
            pb={8}
            pl={12}
            pr={12}
            style={(theme) => ({
                // Team-specific gradient backgrounds
                background: isRadiant
                    ? getGradient({
                        deg: 135,
                        from: alpha(theme.colors.green[2], 0.1),
                        to: alpha(theme.colors.green[3], 0.05)
                      }, theme)
                    : getGradient({
                        deg: 135,
                        from: alpha(theme.colors.red[2], 0.1),
                        to: alpha(theme.colors.red[3], 0.05)
                      }, theme),


                // Subtle borders for definition
                border: `1px solid ${isRadiant
                    ? alpha(theme.colors.green[2], 0.2)
                    : alpha(theme.colors.red[2], 0.2)
                }`,

                // Team-specific glow effect
                boxShadow: `
                    inset 0 1px 0 ${alpha('white', 0.1)},
                    0 0 12px ${alpha(isRadiant ? theme.colors.green[2] : theme.colors.red[2], 0.3)}
                `,

                borderRadius: theme.radius.md,

            })}
        >
            <TextLgBold c={isRadiant ? 'green.2' : 'red.2'}>
                {faction}
            </TextLgBold>

            <Group
                w='80vw'
                h={40}
                gap={1}
                p={0}
                wrap="nowrap"
                style={{borderRadius: 8, overflow: 'clip'}}
                align="start"
                justify="start"
            >
                {heroPicks.map((heroId, idx) => (
                    <HeroIcon key={`${heroId}-${idx}`} hero_id={heroId} />
                ))}
            </Group>

            <Group>
                <TextLgRegular ta="left" h='auto' w='100%' lineClamp={1}>
                    {teamName}
                </TextLgRegular>
            </Group>
        </Stack>
    );
}
