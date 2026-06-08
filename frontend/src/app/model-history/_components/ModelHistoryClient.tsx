"use client";

import { Suspense, useState, useMemo, useEffect } from "react";
import dynamic from "next/dynamic";
import { Skeleton } from "@mantine/core";
import useSWR from "swr";
import fetchModelHistory from "@/api-client/fetch-model-history";
import { weightedMean } from "@/utils/weighted-mean";
import type { ModelHistoryRequest, AggregateBy, HistoryRange, ModelHistoryResponse } from "@/types/contracts/index";
import ModelHistorySkeleton from './ModelHistorySkeleton';
import ModelHistoryMobileView from './ModelHistoryMobileView';

// Code-split the recharts-backed desktop chart view so its bundle only loads
// client-side when this page renders (ssr:false avoids shipping it to the server).
const ModelHistoryGraphView = dynamic(() => import('./ModelHistoryGraphView'), {
    ssr: false,
    loading: () => <Skeleton h={560} radius="md" />,
});

const historyRangeOptions = [
    { label: '7D', value: '7' },
    { label: '30D', value: '30' },
    { label: '90D', value: '90' },
    { label: '365D', value: '365' },
    { label: 'All', value: '0' },
];

const chartMetricsData = [
    { name: 'accuracy', type: 'line', color: 'blue.3' },
    { name: 'auc', type: 'line', color: 'green.3' },
    { name: 'root_brier', type: 'line', color: 'red.3' },
];


const chartMetricsNames = chartMetricsData.map(ds => ds.name);

export type DataDisplayOptions = 'history' | 'calibration';

function ModelHistoryContent() {
    const [historyRange, setHistoryRange] = useState<HistoryRange>(7); // Defaults to 1 week
    const [aggregateBy, setAggregateBy] = useState<AggregateBy>(1); // Defaults to daily aggregation
    const [selectedMetrics, setSelectedMetrics] = useState<string[]>(chartMetricsNames);
    const [dataDisplayOption, setDataDisplayOption] = useState<DataDisplayOptions>('history');

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

    const historyFetcher = ({historyRange, aggregateBy}: {historyRange: HistoryRange, aggregateBy: AggregateBy}) => {
        const params: ModelHistoryRequest = { history_range: historyRange, aggregate_by: aggregateBy };
        return fetchModelHistory(params);
    };

    const fallbackData: ModelHistoryResponse = { history: [], calibration_plot: { bins: [] } };

    const { data } = useSWR({historyRange, aggregateBy}, historyFetcher, {
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        refreshInterval: 0,
        suspense: true,
        fallbackData,
    });

    const historyData = data.history;
    const calibrationData = data.calibration_plot;

    const summaryStats = useMemo(() => {
        const dataExists = historyData && historyData.length > 0;
        if (!dataExists) {
            return {
                averageAccuracy: 0, averageAuc: 0, averageRootBrier: 0,
                maxAccuracy: 0, maxAuc: 0, minRootBrier: 0,
            };
        }
        // Averages are weighted by each bucket's match_count so a low-volume day
        // can't swing the headline number — they reflect performance per match,
        // not per bucket. Root brier is squared back to the (mean-of-squares)
        // brier score before weighting, then re-rooted, since averaging roots is
        // not valid.
        const averageAccuracy = weightedMean(historyData, e => e.accuracy ?? 0);
        const averageAuc = weightedMean(historyData, e => e.auc ?? 0);
        const averageRootBrier = Math.sqrt(weightedMean(historyData, e => (e.root_brier ?? 0) ** 2));
        const maxAccuracy = Math.max(...historyData.map(e => e.accuracy ?? 0));
        const maxAuc = Math.max(...historyData.map(e => e.auc ?? 0));
        const minRootBrier = Math.min(...historyData.map(e => e.root_brier ?? 1));
        return { averageAccuracy, averageAuc, averageRootBrier, maxAccuracy, maxAuc, minRootBrier };
    }, [historyData]);

    const activeChartSeries = chartMetricsData.filter(ds => selectedMetrics.includes(ds.name));

    const handleDataDisplayOptionChange = (option: DataDisplayOptions) => {
        setDataDisplayOption(option);
    };

    const sharedProps = {
        historyRange,
        onHistoryRangeChange: handleHistoryRangeChange,
        historyRangeOptions,
        chartMetricsData,
        selectedMetrics,
        onSelectedMetricsChange: setSelectedMetrics,
        historyData,
        dataDisplayOption,
        onDataDisplayOptionChange: handleDataDisplayOptionChange,
        calibrationData,
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
