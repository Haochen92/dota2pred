
import Image from "next/image";
import { Flex } from "@mantine/core";

type HeroIconProps = {
    hero_id: number
    hero_name?: string
    minHeight?: number
    minWidth?: number
}

export default function HeroIcon ({hero_id, hero_name, minHeight, minWidth } : HeroIconProps) {

    return (
    <Flex justify='center' align='center' w='100%' h='100%' mih={minHeight || 0} miw={minWidth || 0} pos='relative'>
        <Image
            fill={true}
            src={`/icons/heroes/${hero_id}.png`}
            alt={hero_name ? `${hero_name}.png` : `${hero_id}.png`}
            style={{objectFit:"cover"}}
        />
    </Flex>
    )
}
