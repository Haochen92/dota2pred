import { Group, Stack } from '@mantine/core';
import HeroIcon from '@/components/icons/HeroIcon';
import { TextMdRegular } from '@/components/typography/TextVariants';

type TeamDisplayProps = {
    teamName: string;
    heroPicks: number[];
};

export default function TeamDisplay({ teamName, heroPicks }: TeamDisplayProps) {
    return (
        <Stack align="flex-start" justify="center" gap={4} flex={2.5} h='100%' pt={8} pb={8} pl={12} pr={12}>
            <Group
                w={216} h={30} gap={1} p={0}
                wrap="nowrap" style={{borderRadius:8, overflow:'clip'}}
                align="start" justify="start"
            >
                {heroPicks.map((heroId) => (
                    <HeroIcon key={heroId} hero_id={heroId}/>
                ))}
            </Group>
            <Group>
                <TextMdRegular ta="left" h='auto' w='100%' lineClamp={1}>{teamName}</TextMdRegular>
            </Group>
        </Stack>
    );
}
