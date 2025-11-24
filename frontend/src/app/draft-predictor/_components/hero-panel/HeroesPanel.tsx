import { SimpleGrid } from "@mantine/core";
import HerosContainer from "./HerosContainer";
import HeroesPanelMobile from "./HeroesPanelMobile";

export default function HeroesPanel() {
    return(
        <>
            <SimpleGrid
                visibleFrom='sm'
                cols={{base: 2, sm: 1, md: 2}}
                spacing='24' w='100%' h='auto'
                p={20}
                bg='gray.9'
                style={{borderRadius: '24px'}}
            >
                {/* Desktop View, full display of all 4 attributes grid */}
                <HerosContainer attribute="strength" />
                <HerosContainer attribute="intelligence" />
                <HerosContainer attribute="agility" />
                <HerosContainer attribute="universal" />
            </SimpleGrid>
            {/* Mobile View, single attribute display*/}
            <HeroesPanelMobile />

        </>

    )
}
