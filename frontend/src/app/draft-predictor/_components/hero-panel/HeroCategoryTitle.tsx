import Image from "next/image";
import { Box } from "@mantine/core";
import classes from "../../draft-predictor.module.css";

export type AttributeTypes = "strength" | "agility" | "intelligence" | "universal";

const attributeShortMapping: Record<AttributeTypes, string> = {
    strength: "str",
    agility: "agi",
    intelligence: "int",
    universal: "uni",
};

// Dota attribute colours, mapped onto theme tokens for the brutalist accent.
const attributeAccent: Record<AttributeTypes, string> = {
    strength: "var(--mantine-color-red-4)",
    agility: "var(--mantine-color-green-4)",
    intelligence: "var(--mantine-color-blue-3)",
    universal: "var(--mantine-color-purple-4)",
};

export type HeroCategoryTitleProps = {
    attribute: AttributeTypes;
};

export default function HeroCategoryTitle({ attribute }: HeroCategoryTitleProps) {
    return (
        <Box
            className={classes.tag}
            style={{ "--tag-accent": attributeAccent[attribute] } as React.CSSProperties}
        >
            <Image src={`/icons/hero_attributes/${attribute}.svg`} alt={attribute} width={18} height={18} />
            {attribute}
        </Box>
    );
}

export function HeroCategoryTitleMobile({ attribute }: HeroCategoryTitleProps) {
    return (
        <Box
            component="span"
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: 1,
            }}
        >
            <Image src={`/icons/hero_attributes/${attribute}.svg`} alt={attribute} width={14} height={14} />
            {attributeShortMapping[attribute]}
        </Box>
    );
}
