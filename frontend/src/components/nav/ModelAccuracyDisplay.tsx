'use client';

import fetchModelHistory from '@/api/fetch-model-history';
import { Title, Center, NumberFormatter } from '@mantine/core';
import useSWR from 'swr';

const fetcher = () => {
    return fetchModelHistory({ history_range: 7, aggregate_by: 7 });
}

export default function ModelAccuracyDisplay() {

    const { data, error } = useSWR(
        'model-accuracy', fetcher,
        {
            revalidateOnReconnect: true,
            refreshInterval: 60 * 60 * 24 * 1000, // 24 hours
            suspense: true,
            fallbackData: { history: [] }

        }
    );

    const latestAccuracy = data?.history?.[0]?.accuracy ?? 0;
    const displayAccuracyPercent = latestAccuracy * 100;

    return (
        <Center h="100%" w="100%">
            <Title order={4} fw={500} c='black'>
                <NumberFormatter decimalScale={0} value={displayAccuracyPercent} suffix="%" />
            </Title>
        </Center>
    );
}
