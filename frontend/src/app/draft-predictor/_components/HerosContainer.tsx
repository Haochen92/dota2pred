import { useState, useEffect, useMemo } from 'react'
import { SimpleGrid, Stack } from "@mantine/core"
import HeroIcon from "@/components/icons/HeroIcon"
import HeroCategoryTitle from "./HeroCategoryTitle";
import type { HeroCategoryTitleProps } from "./HeroCategoryTitle";
import { useConstantsStore } from "@/hooks/useConstantsStore";
import { HeroImageData } from "@/types/contracts";

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
    }, [fetchConstants]);

    if (isLoading) {
        return <div>Loading...</div>;
    }

    console.log(heroesData);

    return (
    <Stack w='100%' h='100%' align='flex-start' justify='flex-start' gap={16}>
        <HeroCategoryTitle attribute={attribute} />
        <SimpleGrid cols={7} spacing={8} h='auto'>
            {heroesData.map(hero => (
                <HeroIcon
                    key={hero.hero_id}
                    hero_id={hero.hero_id}
                    hero_name={hero.hero_name}
                    minHeight={45}
                    minWidth={80}
                />
            ))}
        </SimpleGrid>
    </Stack>
    );
}
