import { Group, Flex } from "@mantine/core"
import { TextSmBold } from "@/components/typography/TextVariants";

export default function TableHeader() {
    return (
        <Group
            w='100%'
            align="center" justify="flex-start"
            p={0} gap={0} wrap='nowrap'
            style={{ borderBottom: '3px solid var(--mantine-color-default-border)'}}
        >
            {/* Column 1: Time & Date */}
            <Group w={120} gap={16} pl={12} pr={12} pt={24} pb={24}>
                <TextSmBold>Time & Date</TextSmBold>
            </Group>

            {/* Column 2: Tournament/ League */}
            <Group flex={1.5} pl={12} pr={12} gap={16} pt={24} pb={24}>
                <TextSmBold>Tournament</TextSmBold>
            </Group>

            {/* Column 3: Radiant Team */}
            <Group flex={2.5} pl={12} pr={12} gap={16} pt={24} pb={24}>
                <TextSmBold c='green.2'>Radiant Team</TextSmBold>
            </Group>

            {/* Column 4: Dire Team */}
            <Group flex={2.5} pl={12} pr={12} gap={16} pt={24} pb={24}>
                <TextSmBold c='red.2'>Dire Team</TextSmBold>
            </Group>

            {/* Column 5: Prediction */}
            <Group flex={1.5} gap={16} pl={12} pr={12} pt={24} pb={24}>
                <TextSmBold>Prediction</TextSmBold>
            </Group>

            {/* Column 6: Actual Outcome */}
            <Group flex={1.5} gap={16} pl={12} pr={12} pt={24} pb={24}>
                <TextSmBold>Outcome</TextSmBold>
            </Group>

            {/* Column 7: Correct */}
            <Group flex={0.5} pt={24} pb={24} justify='center'>
                <TextSmBold>Correct</TextSmBold>
            </Group>
        </Group>
    )
}
