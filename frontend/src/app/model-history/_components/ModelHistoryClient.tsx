"use client";

import { Suspense, useState, useMemo, useEffect } from "react";
import useSWR from "swr";
import fetchModelHistory from "@/api/fetch-model-history";
import type { ModelHistoryRequest, AggregateBy, HistoryRange } from "@/types/contracts/index";
import ModelHistorySkeleton from './ModelHistorySkeleton';
import ModelHistoryGraphView from './ModelHistoryGraphView';
import ModelHistoryMobileView from './ModelHistoryMobileView';

const historyRangeOptions = [
    { label: '7D', value: '7' },
    { label: '30D', value: '30' },
    { label: '90D', value: '90' },
    { label: '365D', value: '365' },
    { label: 'All', value: '0' },
];

const chartMetricsData = [
    { name: 'accuracy', type: 'line', color: 'blue.3' },
    { name: 'precision', type: 'line', color: 'green.3' },
    { name: 'recall', type: 'line', color: 'red.3' },
];

const chartMetricsNames = chartMetricsData.map(ds => ds.name);

function ModelHistoryContent() {
    const [historyRange, setHistoryRange] = useState<HistoryRange>(7); // Defaults to 1 week
    const [aggregateBy, setAggregateBy] = useState<AggregateBy>(1); // Defaults to daily aggregation
    const [selectedMetrics, setSelectedMetrics] = useState<string[]>(chartMetricsNames);

    // Adjust aggregation granularity when history range changes
    useEffect(() => {
        switch (historyRange) {
            case 7:
            case 30:
                setAggregateBy(1); // Daily
                break;
            case 90:
            case 365:
                setAggregateBy(7); // Weekly
                break;
            case 0:
                setAggregateBy(30); // Monthly
                break;
            default:
                setAggregateBy(1);
        }
    }, [historyRange]);

    const handleHistoryRangeChange = (value: string) => {
        setHistoryRange(Number(value) as HistoryRange);
    };

    const historyRequestKey = useMemo(() => ['model_history', { historyRange, aggregateBy }], [historyRange, aggregateBy]);

    const historyFetcher = () => {
        const params: ModelHistoryRequest = { history_range: historyRange, aggregate_by: aggregateBy };
        return fetchModelHistory(params);
    };

    const { data } = useSWR(historyRequestKey, historyFetcher, {
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        refreshInterval: 0,
        suspense: true,
        fallbackData: { history: [] }
    });

    const historyData = data.history;

    const summaryStats = useMemo(() => {
        const dataExists = historyData && historyData.length > 0;
        if (!dataExists) {
            return {
                averageAccuracy: 0, averagePrecision: 0, averageRecall: 0,
                maxAccuracy: 0, maxPrecision: 0, maxRecall: 0,
            };
        }
        const count = historyData.length;
        const averageAccuracy = historyData.reduce((sum, entry) => sum + (entry.accuracy ?? 0), 0) / count;
        const averagePrecision = historyData.reduce((sum, entry) => sum + (entry.precision ?? 0), 0) / count;
        const averageRecall = historyData.reduce((sum, entry) => sum + (entry.recall ?? 0), 0) / count;
        const maxAccuracy = Math.max(...historyData.map(e => e.accuracy ?? 0));
        const maxPrecision = Math.max(...historyData.map(e => e.precision ?? 0));
        const maxRecall = Math.max(...historyData.map(e => e.recall ?? 0));
        return { averageAccuracy, averagePrecision, averageRecall, maxAccuracy, maxPrecision, maxRecall };
    }, [historyData]);

    const activeChartSeries = chartMetricsData.filter(ds => selectedMetrics.includes(ds.name));

    const sharedProps = {
        historyRange,
        onHistoryRangeChange: handleHistoryRangeChange,
        historyRangeOptions,
        chartMetricsData,
        selectedMetrics,
        onSelectedMetricsChange: setSelectedMetrics,
        historyData,
    };

    return (
        <>
            <ModelHistoryGraphView
                visibilityBreakpoint="sm"
                activeChartSeries={activeChartSeries}
                summaryStats={summaryStats}
                {...sharedProps}
            />
            <ModelHistoryMobileView
                visibilityBreakpoint="sm"
                summaryStats={summaryStats}
                {...sharedProps}
            />
        </>
    );
}

export default function ModelHistoryClient(){
    return (
        <Suspense fallback={<ModelHistorySkeleton />}>
            <ModelHistoryContent />
        </Suspense>
    );
}
