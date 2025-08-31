
import Image from "next/image";
import { Flex } from "@mantine/core";

type HeroIconProps = {
    hero_id: number
}

export default function HeroIcon ({hero_id} : HeroIconProps) {

    return (
    <Flex justify='center' align='center' w='100%' h='100%' pos='relative'>
        <Image
            fill={true}
            src={`/icons/heroes/${hero_id}.png`}
            alt={`${hero_id}.png`}
            style={{objectFit:"contain"}}
        />
    </Flex>

    )

}
