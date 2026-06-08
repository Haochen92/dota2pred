"use client";

import dynamic from 'next/dynamic';
import { Group, Stack, SegmentedControl, Paper, Chip, SimpleGrid, Skeleton } from '@mantine/core';
import { LineChart } from '@mantine/charts';
import CustomToolTip from '@/components/charts/CustomToolTip';
import { dateFormatter } from '@/utils/date-formatter';
import { StatCard } from './StatCard';
import type { AggregateBy, HistoryRange, CalibrationPlotPoint } from '@/types/contracts';
import brut from '@/styles/brutalist.module.css';

// Code-split the calibration chart: it only mounts when the user toggles to it.
const CalibrationPlot = dynamic(() => import('./CalibrationPlot'), {
  ssr: false,
  loading: () => <Skeleton h={400} radius="md" />,
});

const segClassNames = { root: brut.segRoot, indicator: brut.segIndicator, label: brut.segLabel };

// Display names for metric toggles (values stay as the raw metric keys).
const METRIC_LABELS: Record<string, string> = { accuracy: 'Accuracy', auc: 'AUC', root_brier: 'Root Brier' };

interface ChartSeriesConfig { name: string; type: string; color: string; }

interface DateRangeControlProps {
  historyRange: HistoryRange;
  historyRangeOptions: { label: string; value: string }[];
  onHistoryRangeChange: (value: string) => void;
}

function DateRangeControl({ historyRange, historyRangeOptions, onHistoryRangeChange }: DateRangeControlProps) {
  return (
    <SegmentedControl
      id='history-range-control'
      value={historyRange.toString()}
      data={historyRangeOptions}
      onChange={onHistoryRangeChange}
      radius={8}
      classNames={segClassNames}
      withItemsBorders={false}
      transitionDuration={150}
      transitionTimingFunction='linear'
    />
  );
}

interface DisplayControlProps {
  dataDisplayOption: 'history' | 'calibration';
  onDataDisplayOptionChange: (option: 'history' | 'calibration') => void;
}

function DisplayControl({ dataDisplayOption, onDataDisplayOptionChange }: DisplayControlProps) {
  return (
    <SegmentedControl
      id='data-display-option-control'
      value={dataDisplayOption}
      data={[
        { label: 'History', value: 'history' },
        { label: 'Calibration', value: 'calibration' },
      ]}
      onChange={(value) => onDataDisplayOptionChange(value as 'history' | 'calibration')}
      radius={8}
      classNames={segClassNames}
      withItemsBorders={false}
      transitionDuration={150}
      transitionTimingFunction='linear'
    />
  );
}

interface MetricsControlProps {
  chartMetricsData: ChartSeriesConfig[];
  selectedMetrics: string[];
  onSelectedMetricsChange: (metrics: string[]) => void;
}

function MetricsControl({ chartMetricsData, selectedMetrics, onSelectedMetricsChange }: MetricsControlProps) {
  return (
    <Chip.Group multiple value={selectedMetrics} onChange={onSelectedMetricsChange}>
      <Stack justify='flex-start' gap={8}>
        {chartMetricsData.map((metric) => (
          <Chip
            key={metric.name} value={metric.name} color={metric.color} size='sm'
            classNames={{ label: brut.chipLabel, iconWrapper: brut.hideIcon }}
            styles={{ label: { width: 130, justifyContent: 'center' } }}
          >
            {METRIC_LABELS[metric.name] ?? metric.name}
          </Chip>
        ))}
      </Stack>
    </Chip.Group>
  );
}

interface LineChartComponentProps {
  historyData: any[];
  activeChartSeries: ChartSeriesConfig[];
  chartMetricsData: ChartSeriesConfig[];
  selectedMetrics: string[];
  onSelectedMetricsChange: (metrics: string[]) => void;
}

function LineChartComponent({
  historyData,
  activeChartSeries,
  chartMetricsData,
  selectedMetrics,
  onSelectedMetricsChange,
}: LineChartComponentProps) {
  return (
    <Group align="flex-start">
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
              interval: 'preserveStartEnd',
              padding: { left: 20, right: 20 },
              minTickGap: 30,
            }}
            yAxisProps={{domain:[0, 1]}}
            tooltipProps={{
              content: ({ label, payload }) => <CustomToolTip label={label} payload={payload} />,
            }}
            referenceLines={[{ y: 0.5, label: '0.5', stroke: 'white', strokeDasharray: '3 3' }]}
            connectNulls={false}
          />
        </Group>
        <MetricsControl
          chartMetricsData={chartMetricsData}
          selectedMetrics={selectedMetrics}
          onSelectedMetricsChange={onSelectedMetricsChange}
        />
      </Group>
  );
}

export interface ModelHistoryGraphViewProps {
  visibilityBreakpoint?: string; // Mantine breakpoint at which to hide this (using hiddenFrom)
  historyRange: HistoryRange;
  onHistoryRangeChange: (value: string) => void;
  historyRangeOptions: { label: string; value: string }[];
  chartMetricsData: ChartSeriesConfig[];
  selectedMetrics: string[];
  onSelectedMetricsChange: (metrics: string[]) => void;
  historyData: any[];
  activeChartSeries: ChartSeriesConfig[];
  summaryStats: {
    averageAccuracy: number; averageAuc: number; averageRootBrier: number;
    maxAccuracy: number; maxAuc: number; minRootBrier: number;
  };
  dataDisplayOption: 'history' | 'calibration';
  onDataDisplayOptionChange: (option: 'history' | 'calibration') => void;
  calibrationData: CalibrationPlotPoint;
}

export function ModelHistoryGraphView({
  visibilityBreakpoint,
  historyRange,
  onHistoryRangeChange,
  historyRangeOptions,
  chartMetricsData,
  selectedMetrics,
  onSelectedMetricsChange,
  historyData,
  activeChartSeries,
  summaryStats,
  dataDisplayOption,
  onDataDisplayOptionChange,
  calibrationData,
}: ModelHistoryGraphViewProps) {
  return (
    <Paper
      visibleFrom={visibilityBreakpoint}
      p='xl'
      gap='xl'
      component={Stack}
      w='100%'
      h='auto'
      bg='gray.8'
      className={brut.panel}
    >
      <Group justify='space-between' align='center' px={8}>
        <DateRangeControl
          historyRange={historyRange}
          historyRangeOptions={historyRangeOptions}
          onHistoryRangeChange={onHistoryRangeChange}
        />
        <DisplayControl
          dataDisplayOption={dataDisplayOption}
          onDataDisplayOptionChange={onDataDisplayOptionChange}
        />
      </Group>
      {dataDisplayOption === 'history' ?
        <LineChartComponent
          historyData={historyData}
          activeChartSeries={activeChartSeries}
          chartMetricsData={chartMetricsData}
          selectedMetrics={selectedMetrics}
          onSelectedMetricsChange={onSelectedMetricsChange}
        /> :
        <CalibrationPlot
          calibrationData={calibrationData}
          title="Calibration Plot"
          height={400}
          width="100%"
          visibilityBreakpoint={visibilityBreakpoint}
        />
      }
      {dataDisplayOption === 'history' && (
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" px={8}>
          <StatCard
            metric="accuracy"
            color="blue.3"
            average={summaryStats.averageAccuracy}
            max={summaryStats.maxAccuracy}
          />
          <StatCard
            metric="auc"
            color="green.3"
            average={summaryStats.averageAuc}
            max={summaryStats.maxAuc}
          />
          <StatCard
            metric="root brier"
            color="red.3"
            average={summaryStats.averageRootBrier}
            max={summaryStats.minRootBrier}
            secondaryLabel="Min"
          />
        </SimpleGrid>
      )}
    </Paper>
  );
}

export default ModelHistoryGraphView;
