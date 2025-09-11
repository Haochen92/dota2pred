import { SimpleGrid, Flex } from "@mantine/core";
import HerosContainer from "./HerosContainer";

export default function HeroesPanel() {
    return(
            <SimpleGrid
                cols={{base: 2, sm: 1, lg: 2}}
                spacing='24' w='100%' h='auto'
                p={20}
                bg='gray.9'
                style={{borderRadius: '24px'}}
            >
                <HerosContainer attribute="strength" />
                <HerosContainer attribute="intelligence" />
                <HerosContainer attribute="agility" />
                <HerosContainer attribute="universal" />
            </SimpleGrid>
    )
}
