import { useEffect, useMemo } from 'react'
import { SimpleGrid, Stack, Skeleton } from "@mantine/core"
import HeroCategoryTitle from './HeroCategoryTitle';
import type { HeroCategoryTitleProps } from "./HeroCategoryTitle";
import { useConstantsStore } from "@/hooks/useConstantsStore";
import { HeroImageData } from "@/types/contracts";
import useDraftContext from '@/hooks/useDraftContext';
import SelectableHero from '../shared/SelectableHero';

const attributeMapping = {
    'strength': 'str',
    'agility': 'agi',
    'intelligence': 'int',
    'universal': 'all'
}


export default function HerosContainer({attribute}: HeroCategoryTitleProps) {

    const mapped_attribute = attributeMapping[attribute];

    const isLoading = useConstantsStore(state => state.isLoading);
    const hasFetched = useConstantsStore(state => state.hasFetched);
    const fetchConstants = useConstantsStore(state => state.fetchConstants);

    const allHeroes = useConstantsStore(state => state.heroes);

    // Memoise filter and sort logic
    const heroesData: HeroImageData[] = useMemo(
        () => allHeroes
        .filter(hero => hero.primary_attr === mapped_attribute)
        .sort((a, b) => a.hero_name.localeCompare(b.hero_name)),
        [allHeroes, mapped_attribute]
    );

    useEffect(() => {
        if (!hasFetched) {
           void fetchConstants();
        }
    }, [hasFetched, fetchConstants]);

    const { form, handleHeroPick } = useDraftContext();
    const { radiantTeam, direTeam, activeSlot } = form.values;

    // Create a set of already picked heroes for quick lookup
    const pickedHeroes = useMemo(() => {
        return new Set([...radiantTeam, ...direTeam]);
    }, [radiantTeam, direTeam]);

    const canPick = activeSlot !== null;

    if (isLoading) {
        return (
            <>
                <Stack w='100%' h='100%' align='flex-start' justify='flex-start' gap={16} visibleFrom='sm'>
                    {/* Desktop View, visibleFrom='sm' */ }
                    <HeroCategoryTitle attribute={attribute} />
                    <SimpleGrid cols={7} spacing={8} h='auto'>
                        {Array.from({length:35}).map((_, i) => (
                            <Skeleton key={i} height={55} width={80} radius='md' />
                        ))}
                    </SimpleGrid>
                </Stack>
                <Stack w='100%' h='100%' align='flex-start' justify='flex-start' gap={16} hiddenFrom='sm'>
                    <HeroCategoryTitle attribute={attribute} />
                    <SimpleGrid cols={5} spacing={4} h='auto'>
                        {Array.from({length:35}).map((_, i) => (
                            <Skeleton key={i} height={45} width={70} radius='md' />
                        ))}
                    </SimpleGrid>
                </Stack>
            </>

        );
    }

    if (process.env.NODE_ENV === 'development') {
        console.log(heroesData);
    }

    return (
    <>
    <Stack w='100%' h='100%' align='flex-start' justify='flex-start' gap={16} visibleFrom='sm'>
        {/* Desktop View, visibleFrom='sm' */}
        <HeroCategoryTitle attribute={attribute} />
        <SimpleGrid cols={7} spacing={8} h='auto'>
            {heroesData.map(hero => (
                <SelectableHero
                    key={hero.hero_id}
                    hero_id={hero.hero_id}
                    hero_name={hero.hero_name}
                    minHeight={55}
                    minWidth={80}
                    isPicked={pickedHeroes.has(hero.hero_id)}
                    canPick={canPick}
                    handlePick={handleHeroPick}
                />
            ))}
        </SimpleGrid>
    </Stack>
    <Stack w='100%' h='100%' align='center' justify='center' gap={16} hiddenFrom='sm'>
        {/* mobile View, visibleFrom='sm' */}
        <SimpleGrid cols={5} spacing={8} h='auto'>
            {heroesData.map(hero => (
                <SelectableHero
                    key={hero.hero_id}
                    hero_id={hero.hero_id}
                    hero_name={hero.hero_name}
                    minHeight={45}
                    minWidth={62}
                    isPicked={pickedHeroes.has(hero.hero_id)}
                    canPick={canPick}
                    handlePick={handleHeroPick}
                />
            ))}
        </SimpleGrid>
    </Stack>

    </>

    );
}
