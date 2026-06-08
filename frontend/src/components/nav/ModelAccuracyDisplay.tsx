// components/AccuracyTitle.tsx
'use client';

import useSWR from 'swr';
import fetchModelHistory from '@/api-client/fetch-model-history';
import { weightedMean } from '@/utils/weighted-mean';
import { Title, NumberFormatter, Center, Loader } from '@mantine/core';
import type { ModelHistoryRequest, AggregateBy, HistoryRange } from '@/types/contracts';

// Same params as the Model History 7D card so the two figures are obviously the
// same request. The weighted mean below is bucketing-invariant, so the daily
// aggregation here produces an identical number to any other aggregate_by.
//
// Share SWR cache with ModelHistoryClient by using the identical key shape
// ({ historyRange, aggregateBy }) and fetcher args — SWR can only dedupe when
// the serialized keys match.
const historyFetcher = ({ historyRange, aggregateBy }: { historyRange: HistoryRange, aggregateBy: AggregateBy }) => {
    const params: ModelHistoryRequest = { history_range: historyRange, aggregate_by: aggregateBy };
    return fetchModelHistory(params);
};

function AccuracyTitle() {
    const { data, error, isLoading } = useSWR(
        { historyRange: 7 as HistoryRange, aggregateBy: 1 as AggregateBy },
        historyFetcher,
        {
            revalidateOnReconnect: true,
            refreshInterval: 60 * 60 * 24 * 1000,
        }
    );

    // Match-weighted accuracy across the whole 7-day window — the same figure the
    // Model History 7D card shows. Weighting is invariant to bucketing, so this
    // matches regardless of aggregate_by; reading history[0] alone would only
    // reflect a single (often partial) bucket.
    const accuracy = weightedMean(data?.history ?? [], e => e.accuracy ?? 0);
    const displayAccuracyPercent = accuracy * 100;

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
    );
}
