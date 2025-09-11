import Image from "next/image";
import { Group } from "@mantine/core";

import { TextSpecial } from "@/components/typography/TextVariants";

export type AttributeTypes = "strength" | "agility" | "intelligence" | "universal";

export type HeroCategoryTitleProps = {
  attribute: AttributeTypes;
};

export default function HeroCategoryTitle({ attribute }: HeroCategoryTitleProps) {
  return (
    <Group gap={8} justify="flex-start" align='center'>
        <Image src={`/icons/hero_attributes/${attribute}.svg`} alt={attribute} width={24} height={24} />
        <TextSpecial tt='uppercase'>
            {attribute}
        </TextSpecial>
    </Group>
  );
}
