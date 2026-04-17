import Image from "next/image";
import { Group } from "@mantine/core";

import { TextSpecial, TextMdBold } from "@/components/typography/TextVariants";

export type AttributeTypes = "strength" | "agility" | "intelligence" | "universal";
const attributeMapping = {
    'strength': 'str',
    'agility': 'agi',
    'intelligence': 'int',
    'universal': 'uni'
};

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

export function HeroCategoryTitleMobile({ attribute }: HeroCategoryTitleProps) {
  const attributeShort = attributeMapping[attribute];
  return (
    <Group gap={4} justify="flex-start" align='center'>
        <Image src={`/icons/hero_attributes/${attribute}.svg`} alt={attribute} width={12} height={12} />
        <TextMdBold tt='uppercase'>
            {attributeShort}
        </TextMdBold>
    </Group>
  );
}
