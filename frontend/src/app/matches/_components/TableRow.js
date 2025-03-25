'use client'

import { Group, Stack, Text } from '@mantine/core'

export default function TableRow({matchData}) {
    return(
        <Group>
            <Stack id='matchDate'>
                <Text></Text>
            </Stack>
            <Group id='tournament'>

            </Group>
            <Stack id='teamRadiant'>
                <Group></Group>
                <Text></Text>
            </Stack>
            <Stack id='teamDire'>
                <Group></Group>
                <Text></Text>
            </Stack>
            <Group id='prediction'>
                <Text></Text>
                <Image />
            </Group>
            <Group id='result'>
                <Text></Text>
            </Group>
            <Group id='evaluation'>
                <Group>
                    <IconCheck size={24}/>
                </Group>
            </Group>
        </Group>
    )
}