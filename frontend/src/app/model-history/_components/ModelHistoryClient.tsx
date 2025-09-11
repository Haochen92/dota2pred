'use client';

import { Suspense, useState, useMemo, useEffect} from "react";
import useSWR from "swr";
import fetchModelHistory from "@/api/fetch-model-history";
import { Group, Stack, SegmentedControl, Title, Paper, Chip, SimpleGrid } from "@mantine/core";
import { LineChart } from "@mantine/charts";

import { TextLgBold, TextMdRegular } from "@/components/typography/TextVariants";
import type { ModelHistoryRequest, AggregateBy, HistoryRange } from "@/types/contracts/index";

import CustomToolTip from "@/components/charts/CustomToolTip";
import { dateFormatter } from '@/utils/date-formatter';
import { StatCard } from "./StatCard";


const historyRangeOptions = [
        { label: '7D', value: '7' },
        { label: '30D', value: '30' },
        { label: '90D', value: '90' },
        { label: '365D', value: '365' },
        { label: 'All', value: '0' },
]

const chartMetricsData = [
        { name: 'accuracy', type: 'line', color: 'blue.3' },
        { name: 'precision', type: 'line', color: 'green.3' },
        { name: 'recall', type: 'line', color: 'red.3' }
]

const chartMetricsNames = chartMetricsData.map(ds => ds.name);

export default function ModelHistoryClient() {

    const [ historyRange, setHistoryRange ] = useState<HistoryRange>(7); // Defaults to 1 week
    const [ aggregateBy, setAggregateBy ] = useState<AggregateBy>(1); // Defaults to daily aggregation
    const [ selectedMetrics, setSelectedMetrics ] = useState<string[]>(chartMetricsNames);

    const activeChartSeries = chartMetricsData.filter(ds => selectedMetrics.includes(ds.name));

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
                setAggregateBy(30); // Monthly for 'all time'
                break;
            default:
                setAggregateBy(1); // Safe default
        }
    }, [historyRange]);



    const handleHistoryRangeChange = (value: string) => {
        setHistoryRange(Number(value) as HistoryRange);
    }

    const historyRequestKey = useMemo(() => {
        return ['model_history', { historyRange, aggregateBy }];
    }, [historyRange, aggregateBy]);

    const historyFetcher = () => {
        const params: ModelHistoryRequest = {
            history_range: historyRange,
            aggregate_by: aggregateBy
        };
        return fetchModelHistory(params);
    }

    const { data } = useSWR(
        historyRequestKey,
        historyFetcher,
        {
            revalidateOnFocus: true,
            revalidateOnReconnect: true,
            refreshInterval: 0,
            suspense: true,
            fallbackData: {
                history: []
            }
        }
    );


    const historyData = data.history
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

    return (
        <Paper
            p='xl'
            shadow='sm'
            radius='md'
            gap='xl'
            component={Stack}
            w='100%'
            h='auto'
            bg='gray.7'
        >
            <Group
                justify='flex-start' px={8}

            >
                <Title order={3} c='white'>Model Performance History</Title>
            </Group>
            <Group justify='space-between' align='center' px={8}>
                <SegmentedControl
                    bg='transparent'
                    id='history-range-control'
                    value={historyRange.toString()}
                    data={historyRangeOptions}
                    onChange={handleHistoryRangeChange}
                    radius={10}
                    styles={(theme) => ({
                        indicator:{
                            backgroundColor: theme.colors.gray[9],
                        },
                        root:{
                            gap: theme.spacing.xs,
                        },
                        label: {color: theme.colors.gray[0]},

                    })}
                    withItemsBorders={false}
                    transitionDuration={150}
                    transitionTimingFunction='linear'
                />
            </Group>

            <Group align="flex-start">
                <Suspense fallback={<TextMdRegular>Loading chart...</TextMdRegular>}>
                <Group flex={3}>
                    <LineChart
                        data={historyData}
                        dataKey="date"
                        h={400}
                        w='100%'
                        series={activeChartSeries}
                        curveType='step'
                        strokeWidth={2}
                        xAxisProps={{
                            tickFormatter: dateFormatter,
                            // prevent labels from overlapping if they are long
                            interval: 'preserveStartEnd',
                            padding: { left: 20, right: 20 },
                            minTickGap: 30,
                        }}
                        yAxisProps={{domain:[0, 1]}}
                        tooltipProps={{
                            content: ({ label, payload }) => <CustomToolTip label={label} payload={payload} />,
                        }}
                        referenceLines={[
                            { y: 0.5, label: '0.5', stroke: 'white', strokeDasharray: '3 3' }
                        ]}
                        connectNulls={false}
                    />
                </Group>
                <Chip.Group multiple value={selectedMetrics} onChange={setSelectedMetrics}>
                    <Stack justify='flex-start' gap={8}>
                    {chartMetricsData.map((metric) => (
                        <Chip
                            key={metric.name} value={metric.name} color={metric.color} size='sm'
                            styles={{
                                label : {width: '100px'},
                            }}
                        >
                            {metric.name}
                        </Chip>
                    ))}
                    </Stack>
                </Chip.Group>
                </Suspense>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
                    <StatCard
                        metric="accuracy"
                        color="blue.3"
                        average={summaryStats.averageAccuracy}
                        max={summaryStats.maxAccuracy}
                    />
                    <StatCard
                        metric="precision"
                        color="green.3"
                        average={summaryStats.averagePrecision}
                        max={summaryStats.maxPrecision}
                    />
                    <StatCard
                        metric="recall"
                        color="red.3"
                        average={summaryStats.averageRecall}
                        max={summaryStats.maxRecall}
                    />
            </SimpleGrid>
        </Paper>
    )
}
