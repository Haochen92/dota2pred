import HerosContainer from "./HerosContainer";
import { useState } from "react";
import { Chip, Group, Stack, Grid } from "@mantine/core";
import type { HeroCategoryTitleProps } from "./HeroCategoryTitle";
import { HeroCategoryTitleMobile} from "./HeroCategoryTitle";

export default function HeroesPanelMobile() {
    const [ attribute, setAttribute ] = useState<HeroCategoryTitleProps['attribute']>('strength');
    return(
        <Stack hiddenFrom='sm' gap={16}>
            <Chip.Group multiple={false} value={attribute}
                onChange={(value) => setAttribute(value as HeroCategoryTitleProps['attribute'])}
            >
                {/* Controls */}
                <Group justify='space-around' gap={0}>
                    <Chip value='strength' size='xs'>
                            <HeroCategoryTitleMobile attribute="strength" />
                    </Chip>
                    <Chip value='agility' size='xs'>
                            <HeroCategoryTitleMobile attribute="agility" />
                    </Chip>
                    <Chip value='intelligence' size='xs'>
                            <HeroCategoryTitleMobile attribute="intelligence" />
                    </Chip>
                    <Chip value='universal' size='xs'>
                            <HeroCategoryTitleMobile attribute="universal" />
                    </Chip>
                </Group>
            </Chip.Group>
            <Group w='100%' h='auto'
                p={12}
                bg='gray.9'
                style={{borderRadius: '24px'}}
            >
                <HerosContainer attribute={attribute} />
            </Group>
        </Stack>

    );
}
