'use client';

import { Group, Stack, Flex, Skeleton } from '@mantine/core';

// Skeleton version of TeamDisplay component
function TeamDisplaySkeleton() {
    return (
        <Group flex={2} gap={12} pl={12} pr={12} h='100%' align='center'>
            {/* Team name skeleton */}
            <Skeleton height={20} width={120} />

            {/* Hero picks skeletons - typically 5 small circles */}
            <Group gap={4}>
                {Array.from({ length: 5 }, (_, i) => (
                    <Skeleton key={i} height={24} width={24} circle />
                ))}
            </Group>
        </Group>
    );
}

// Skeleton version of TableRow
export function TableRowSkeleton() {
    return (
        <Group
            id='tableRowSkeleton'
            w='100%'
            h={80}
            p={0}
            gap={0}
            wrap='nowrap'
            align="center"
            justify="flex-start"
            style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}
        >
            {/* Column 1: Time & Date */}
            <Stack w={120} h='100%' gap={16} px={12} justify='center'>
                <Stack gap={4}>
                    <Skeleton height={16} width={60} />
                    <Skeleton height={14} width={80} />
                </Stack>
            </Stack>

            {/* Column 2: League */}
            <Group flex={1.5} pl={12} pr={12} h='100%' gap={16}>
                <Skeleton height={16} width={140} />
            </Group>

            {/* Column 3: Radiant Team */}
            <TeamDisplaySkeleton />

            {/* Column 4: Dire Team */}
            <TeamDisplaySkeleton />

            {/* Column 5: Prediction */}
            <Group flex={1.5} gap={16} pl={12} pr={12} pt={0} pb={0}>
                <Group wrap='nowrap' gap={4}>
                    <Skeleton height={16} width={70} />
                    <Skeleton height={16} width={16} circle />
                </Group>
            </Group>

            {/* Column 6: Actual Outcome */}
            <Group flex={1.5} gap={16} pl={12} pr={12}>
                <Skeleton height={16} width={90} />
            </Group>

            {/* Column 7: Correct Prediction */}
            <Flex flex={0.5} h='100%' align='center'>
                <Skeleton height={32} width={32} circle />
            </Flex>
        </Group>
    );
}

export function MatchTableSkeleton({ rowCount = 5 }: { rowCount?: number }) {
    return (
        <Stack w='100%' h='auto'>
            {/* Table Header Skeleton */}
            <Group
                w='100%'
                h={60}
                p={0}
                gap={0}
                wrap='nowrap'
                align="center"
                justify="flex-start"
                style={{
                    borderBottom: '2px solid var(--mantine-color-default-border)',
                    backgroundColor: 'var(--mantine-color-gray-9)'
                }}
            >
                <Stack w={120} px={12} justify='center'>
                    <Skeleton height={14} width={60} />
                </Stack>
                <Group flex={1.5} pl={12} pr={12}>
                    <Skeleton height={14} width={80} />
                </Group>
                <Group flex={2} pl={12} pr={12}>
                    <Skeleton height={14} width={100} />
                </Group>
                <Group flex={2} pl={12} pr={12}>
                    <Skeleton height={14} width={100} />
                </Group>
                <Group flex={1.5} pl={12} pr={12}>
                    <Skeleton height={14} width={80} />
                </Group>
                <Group flex={1.5} pl={12} pr={12}>
                    <Skeleton height={14} width={70} />
                </Group>
                <Flex flex={0.5} align='center' justify='center'>
                    <Skeleton height={14} width={20} />
                </Flex>
            </Group>

            {/* Table Body Skeleton */}
            <Stack>
                {Array.from({ length: rowCount }, (_, i) => (
                    <TableRowSkeleton key={i} />
                ))}
            </Stack>
        </Stack>
    );
}
