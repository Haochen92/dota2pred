"use client";

import { Group, Stack, SegmentedControl, Paper, Chip, SimpleGrid } from '@mantine/core';
import { LineChart } from '@mantine/charts';
import CustomToolTip from '@/components/charts/CustomToolTip';
import { dateFormatter } from '@/utils/date-formatter';
import { StatCard } from './StatCard';
import type { AggregateBy, HistoryRange, CalibrationPlotPoint } from '@/types/contracts';
import { TextSmRegular } from '@/components/typography/TextVariants';
import CalibrationPlot from './CalibrationPlot';

interface ChartSeriesConfig { name: string; type: string; color: string; }

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
  const DateRangeControl = () => (
    <SegmentedControl
      bg='transparent'
      id='history-range-control'
      value={historyRange.toString()}
      data={historyRangeOptions}
      onChange={onHistoryRangeChange}
      radius={10}
      styles={(theme) => ({
        indicator:{
          backgroundColor: theme.colors.gray[9],
        },
        root:{ gap: theme.spacing.xs },
        label: {color: theme.colors.gray[0]},
      })}
      withItemsBorders={false}
      transitionDuration={150}
      transitionTimingFunction='linear'
    />
  )

  const DisplayControl = () => (
    <SegmentedControl
      bg='transparent'
      id='data-display-option-control'
      value={dataDisplayOption}
      data={[
        { label: 'History', value: 'history' },
        { label: 'Calibration', value: 'calibration' },
      ]}
      onChange={(value) => onDataDisplayOptionChange(value as 'history' | 'calibration')}
      radius={10}
      styles={(theme) => ({
        indicator:{
          backgroundColor: theme.colors.gray[9],
        },
        root:{ gap: theme.spacing.xs },
        label: {color: theme.colors.gray[0]},
      })}
      withItemsBorders={false}
      transitionDuration={150}
      transitionTimingFunction='linear'
    />
  )

  const MetricsControl = () => (
    <Chip.Group multiple value={selectedMetrics} onChange={onSelectedMetricsChange}>
      <Stack justify='flex-start' gap={8}>
        {chartMetricsData.map((metric) => (
          <Chip
            key={metric.name} value={metric.name} color={metric.color} size='sm'
            styles={{ label : {width: '100px'} }}
          >
            <TextSmRegular>
              {metric.name}
            </TextSmRegular>
          </Chip>
        ))}
      </Stack>
    </Chip.Group>
  )

  const LineChartComponent = () => (
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
        <MetricsControl/>
      </Group>
  )

  return (
    <Paper
      visibleFrom={visibilityBreakpoint}
      p='xl'
      shadow='sm'
      gap='xl'
      component={Stack}
      w='100%'
      h='auto'
      bg='gray.7'
      style={{ borderRadius: '0' }}
    >
      <Group justify='space-between' align='center' px={8}>
        <DateRangeControl/>
        <DisplayControl/>
      </Group>
      {dataDisplayOption === 'history' ? <LineChartComponent /> :
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
