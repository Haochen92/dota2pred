// components/AccuracyTitle.tsx
'use client';

import useSWR from 'swr';
import fetchModelHistory from '@/api-client/fetch-model-history';
import { Suspense } from 'react';
import { Title, NumberFormatter, Center, Loader } from '@mantine/core';

const fetcher = () => fetchModelHistory({ history_range: 7, aggregate_by: 7 });

function AccuracyTitle() {
    const { data, error, isLoading } = useSWR(
        'model-accuracy',
        fetcher,
        {
            revalidateOnReconnect: true,
            refreshInterval: 60 * 60 * 24 * 1000,
        }
    );

    const latestAccuracy = data?.history?.[0]?.accuracy ?? 0;
    const displayAccuracyPercent = latestAccuracy * 100;

    if (isLoading) {
        return <Loader size="xl" type='dots' color="dark" />;
    }

    if (error) {
        return <Title order={6} fw={500} c='red'>--%</Title>;
    }

    return (
        <>
            <Title order={6} fw={500} hiddenFrom='sm' c='white'>
                <NumberFormatter decimalScale={0} value={displayAccuracyPercent} suffix="%" />
            </Title>
            <Title order={4} fw={500} visibleFrom='sm' c='black'>
                <NumberFormatter decimalScale={0} value={displayAccuracyPercent} suffix="%" />
            </Title>
        </>

    );
}

export default function ModelAccuracyDisplay() {
    return (
        <Center h="100%" w="100%">
                <AccuracyTitle />
        </Center>
    );``
}
