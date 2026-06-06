import { Group, Stack } from '@mantine/core';
import HeroIcon from '@/components/icons/HeroIcon';
import { TextMdBold, TextSmRegular } from '@/components/typography/TextVariants';

type TeamDisplayProps = {
    teamName: string;
    heroPicks: number[];
    faction: 'Radiant' | 'Dire';
};

export default function TeamDisplayCard({ teamName, heroPicks, faction }: TeamDisplayProps) {
    const isRadiant = faction === 'Radiant';

    return (
        <Stack gap={6} w="100%">
            <Group justify="space-between" align="center" wrap="nowrap">
                <TextMdBold c={isRadiant ? 'green.2' : 'red.2'} tt="uppercase" style={{ letterSpacing: 1 }}>
                    {faction}
                </TextMdBold>
                <TextSmRegular c="gray.2" lineClamp={1} ta="right">
                    {teamName}
                </TextSmRegular>
            </Group>

            <Group
                w="100%"
                h={36}
                gap={1}
                p={0}
                wrap="nowrap"
                align="start"
                justify="start"
                style={{
                    borderRadius: 6,
                    overflow: 'clip',
                    border: '2px solid var(--mantine-color-gray-6)',
                }}
            >
                {heroPicks.map((heroId, idx) => (
                    <HeroIcon key={`${heroId}-${idx}`} hero_id={heroId} />
                ))}
            </Group>
        </Stack>
    );
}
