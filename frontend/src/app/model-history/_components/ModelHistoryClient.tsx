'use client';

import { Suspense, useState, useMemo, useEffect} from "react";
import useSWR from "swr";
import fetchModelHistory from "@/api/fetch-model-history";
import { Group, Stack, SegmentedControl, Title, Paper, Chip } from "@mantine/core";
import { LineChart } from "@mantine/charts";

import { TextLgBold, TextMdRegular } from "@/components/typography/TextVariants";
import type { ModelHistoryRequest, AggregateBy, HistoryRange } from "@/types/contracts/index";

import CustomToolTip from "@/components/charts/CustomToolTip";
import { dateFormatter } from '@/utils/date-formatter';


const historyRangeOptions = [
        { label: 'past week', value: '7' },
        { label: 'past month', value: '30' },
        { label: 'past quarter', value: '90' },
        { label: 'past year', value: '365' },
        { label: 'all time', value: '0' },
]

const chartMetricsData = [
        { name: 'accuracy', type: 'line', color: 'blue' },
        { name: 'precision', type: 'line', color: 'green' },
        { name: 'recall', type: 'line', color: 'red' }
]

const chartMetricsNames = chartMetricsData.map(ds => ds.name);

export default function ModelHistoryClient() {

    const [ historyRange, setHistoryRange ] = useState<HistoryRange>(7); // Defaults to 1 week
    const [ aggregateBy, setAggregateBy ] = useState<AggregateBy>(1); // Defaults to daily aggregation
    const [ selectedMetrics, setSelectedMetrics ] = useState<string[]>(chartMetricsNames);

    const activeChartSeries = chartMetricsData.filter(ds => selectedMetrics.includes(ds.name));

    useEffect(() => {
        let newAggregateBy: AggregateBy = 7;
        if ( 7 <= historyRange && historyRange < 30) newAggregateBy = 1; // daily
        else if ( 30 <= historyRange && historyRange <= 90 ) newAggregateBy = 7; // weekly
        else newAggregateBy = 30; // monthly for all time and yearly
        setAggregateBy(newAggregateBy);
    }, [historyRange]);

    const historyFetcher = () => {
        const params: ModelHistoryRequest = {
            history_range: historyRange,
            aggregate_by: aggregateBy
        };
        return fetchModelHistory(params);
    }



    const handleHistoryRangeChange = (value: string) => {
        setHistoryRange(Number(value) as HistoryRange);
    }

    const historyRequestKey = useMemo(() => {
        return ['model_history', { historyRange, aggregateBy }];
    }, [historyRange, aggregateBy]);

    const { data , error } = useSWR(
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


    const historyData = data?.history ?? [];

    return (
        <Paper
            p='md'
            shadow='sm'
            radius='md'
            gap='md'
            component={Stack}
            w='100%'
            h='auto'
            bg='gray.7'
        >
            <Group>
                <Title order={3}>Model Performance History</Title>
            </Group>
            <Group justify='space-between' align='center'>
                <SegmentedControl
                    id='history-range-control'
                    value={historyRange.toString()}
                    data={historyRangeOptions}
                    onChange={handleHistoryRangeChange}
                />
                <Group>
                    <Chip.Group multiple value={selectedMetrics} onChange={setSelectedMetrics}>
                        {chartMetricsData.map(
                            metric => <Chip key={metric.name} value={metric.name} color={metric.color}>{metric.name}</Chip>
                        )}
                    </Chip.Group>
                </Group>
            </Group>

            <Group>
                <Suspense fallback={<TextMdRegular>Loading chart...</TextMdRegular>}>
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
                </Suspense>
            </Group>
        </Paper>
    )
}
