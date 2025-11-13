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
        <Group
            align="flex-start"
            justify="center"
            gap={4}
            flex={2.5}
            h='100%'
        >

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

            <Group wrap='nowrap' justify='space-between' w='100%'>
                <Group >
                    <TextLgBold c={isRadiant ? 'green.2' : 'red.2'}>
                        {faction}
                    </TextLgBold>
                </Group>
                <Group  justify='flex-end'>
                    <TextLgRegular ta="left" h='auto' lineClamp={1} tt='uppercase' >
                        {teamName}
                    </TextLgRegular>
                </Group>
            </Group>
        </Group>
    );
}
