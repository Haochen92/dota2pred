import { Box, SimpleGrid } from "@mantine/core";
import HerosContainer from "./HerosContainer";
import HeroesPanelMobile from "./HeroesPanelMobile";
import classes from "../../draft-predictor.module.css";

export default function HeroesPanel() {
    return (
        <>
            {/* Desktop View — full 2x2 grid of all four attributes */}
            <Box className={classes.panel} p={20} visibleFrom="sm">
                <SimpleGrid cols={{ base: 1, md: 2 }} spacing={28} w="100%">
                    <HerosContainer attribute="strength" />
                    <HerosContainer attribute="intelligence" />
                    <HerosContainer attribute="agility" />
                    <HerosContainer attribute="universal" />
                </SimpleGrid>
            </Box>

            {/* Mobile View — single attribute with tab switcher */}
            <HeroesPanelMobile />
        </>
    );
}
