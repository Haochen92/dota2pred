
import Image from "next/image";
import { Flex } from "@mantine/core";

type HeroAvatarProps = {
    hero_id: number
    hero_name?: string
    minHeight?: number
    minWidth?: number
}

export default function HeroAvatar ({hero_id, hero_name, minHeight, minWidth } : HeroAvatarProps) {

    return (
    <Flex
        justify='center'
        align='center'
        w='100%'
        h='100%'
        mih={minHeight || 0}
        miw={minWidth || 0}
        pos='relative'
    >
        <Image
            fill={true}
            sizes="64px"
            src={`/images/heroes/icons/${hero_id}.png`}
            alt={hero_name ? `${hero_name}.png` : `${hero_id}.png`}
            style={{objectFit:"cover"}}
        />
    </Flex>
    )
}
