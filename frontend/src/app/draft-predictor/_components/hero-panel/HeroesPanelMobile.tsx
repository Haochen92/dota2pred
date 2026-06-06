import HerosContainer from "./HerosContainer";
import { useState } from "react";
import { Box, Chip, Group, Stack } from "@mantine/core";
import type { HeroCategoryTitleProps } from "./HeroCategoryTitle";
import { HeroCategoryTitleMobile } from "./HeroCategoryTitle";
import classes from "../../draft-predictor.module.css";

const ATTRIBUTES: HeroCategoryTitleProps["attribute"][] = [
    "strength",
    "agility",
    "intelligence",
    "universal",
];

export default function HeroesPanelMobile() {
    const [attribute, setAttribute] = useState<HeroCategoryTitleProps["attribute"]>("strength");
    return (
        <Stack hiddenFrom="sm" gap={14}>
            <Chip.Group
                multiple={false}
                value={attribute}
                onChange={(value) => setAttribute(value as HeroCategoryTitleProps["attribute"])}
            >
                <Group justify="space-between" gap={6} wrap="nowrap">
                    {ATTRIBUTES.map((attr) => (
                        <Chip
                            key={attr}
                            value={attr}
                            size="sm"
                            radius={6}
                            classNames={{ label: classes.attrTab }}
                        >
                            <HeroCategoryTitleMobile attribute={attr} />
                        </Chip>
                    ))}
                </Group>
            </Chip.Group>
            <Box className={classes.panel} p={12}>
                <HerosContainer attribute={attribute} />
            </Box>
        </Stack>
    );
}
