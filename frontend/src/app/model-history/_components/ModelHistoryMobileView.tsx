"use client";

import dynamic from 'next/dynamic';
import { Paper, Stack, Group, SegmentedControl, Chip, Table, ScrollArea, Badge, Divider, Skeleton } from '@mantine/core';
import type { HistoryRange, CalibrationPlotPoint } from '@/types/contracts';
import { dateFormatter } from '@/utils/date-formatter';
import { TextMdBold } from '@/components/typography/TextVariants';
import brut from '@/styles/brutalist.module.css';

// Code-split the calibration chart: it only mounts when the user toggles to it.
const CalibrationPlot = dynamic(() => import('./CalibrationPlot'), {
  ssr: false,
  loading: () => <Skeleton h={400} radius="md" />,
});

const segClassNames = { root: brut.segRoot, indicator: brut.segIndicator, label: brut.segLabel };
const METRIC_LABELS: Record<string, string> = { accuracy: 'Accuracy', auc: 'AUC', root_brier: 'Root Brier' };

interface ChartSeriesConfig { name: string; type: string; color: string; }

export interface ModelHistoryMobileViewProps {
  visibilityBreakpoint?: string;
  historyRange: HistoryRange;
  onHistoryRangeChange: (value: string) => void;
  historyRangeOptions: { label: string; value: string }[];
  chartMetricsData: ChartSeriesConfig[];
  selectedMetrics: string[];
  onSelectedMetricsChange: (metrics: string[]) => void;
  historyData: any[];
  calibrationData: CalibrationPlotPoint;
  summaryStats?: {
    averageAccuracy: number; averageAuc: number; averageRootBrier: number;
    maxAccuracy: number; maxAuc: number; minRootBrier: number;
  };
  // External control for display mode
  dataDisplayOption: 'history' | 'calibration';
  onDataDisplayOptionChange: (option: 'history' | 'calibration') => void;
}

const formatPercent = (value: number | null | undefined) =>
  value === null || value === undefined ? '-' : `${(value * 100).toFixed(1)}%`;

export function ModelHistoryMobileView({
  visibilityBreakpoint,
  historyRange,
  onHistoryRangeChange,
  historyRangeOptions,
  chartMetricsData,
  selectedMetrics,
  onSelectedMetricsChange,
  historyData,
  calibrationData,
  summaryStats,
  dataDisplayOption,
  onDataDisplayOptionChange,
}: ModelHistoryMobileViewProps) {

  const handleDisplayOptionChange = (value: string) => {
    const option = value as 'history' | 'calibration';
    onDataDisplayOptionChange(option);
  };

  // Controls
  const DateRangeControl = () => (
    <SegmentedControl
      id='history-range-control-mobile'
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

  const MetricsControl = () => (
    <Chip.Group multiple value={selectedMetrics} onChange={onSelectedMetricsChange}>
      <Group gap={8} wrap='wrap'>
        {chartMetricsData.map(metric => (
          <Chip key={metric.name} value={metric.name} color={metric.color} size='xs' classNames={{ label: brut.chipLabel, iconWrapper: brut.hideIcon }}>
            {METRIC_LABELS[metric.name] ?? metric.name}
          </Chip>
        ))}
      </Group>
    </Chip.Group>
  );

  const DataDisplayControl = () => (
    <SegmentedControl
      id='data-display-control-mobile'
      value={dataDisplayOption}
      data={[
        { label: 'History', value: 'history' },
        { label: 'Calibration', value: 'calibration' },
      ]}
      onChange={handleDisplayOptionChange}
      radius={8}
      classNames={segClassNames}
      withItemsBorders={false}
      transitionDuration={150}
      transitionTimingFunction='linear'
    />
  );

  // Filter columns based on selected metrics; always include date column.
  const activeMetricSet = new Set(selectedMetrics);
  const visibleMetrics = chartMetricsData.filter(m => activeMetricSet.has(m.name));

  return (
    <Paper
      hiddenFrom={visibilityBreakpoint}
      p='lg'
      component={Stack}
      w='100%'
      h='auto'
      bg='gray.8'
      gap='lg'
      className={brut.panel}
    >
      {/* Header controls */}
      <Group justify='space-between' align='center' px={4} wrap='wrap'>
        <DateRangeControl />
        <DataDisplayControl />
      </Group>

      {dataDisplayOption === 'history' ? (
        <>
          <MetricsControl />
          {/* Data Table */}
          <ScrollArea w='100%'>
            <Table
              striped
              highlightOnHover
              withTableBorder={false}
              withColumnBorders={false}
              verticalSpacing='xs'
              horizontalSpacing='md'
              stripedColor='gray.9'
            >
              <Table.Thead>
                <Table.Tr>
                  <Table.Th style={{ width: 120 }}>Date</Table.Th>
                  {visibleMetrics.map(metric => (
                    <Table.Th key={metric.name} style={{ textTransform: 'capitalize' }}>{metric.name}</Table.Th>
                  ))}
                  <Table.Th>Matches</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {historyData.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={visibleMetrics.length + 2} style={{ textAlign: 'center', opacity: 0.6 }}>
                      No history data
                    </Table.Td>
                  </Table.Tr>
                )}
                {historyData.map((row, idx) => (
                  <Table.Tr key={idx}>
                    <Table.Td>{dateFormatter(row.date)}</Table.Td>
                    {visibleMetrics.map(metric => (
                      <Table.Td key={metric.name}>{formatPercent(row[metric.name])}</Table.Td>
                    ))}
                    <Table.Td>{row.match_count}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          <TextMdBold c='gray.1'>Summary Stats</TextMdBold>
          <Divider />

          {/* Minimal Stats Row */}
          {summaryStats && (
            <Group gap={8} wrap='wrap' justify='center'>
              <Badge variant='light' color='blue.3' className={brut.badge}>Accu Avg: {formatPercent(summaryStats.averageAccuracy)}</Badge>
              <Badge variant='light' color='blue.3' className={brut.badge}>Accu Max: {formatPercent(summaryStats.maxAccuracy)}</Badge>
              <Badge variant='light' color='green.3' className={brut.badge}>AUC Avg: {formatPercent(summaryStats.averageAuc)}</Badge>
              <Badge variant='light' color='green.3' className={brut.badge}>AUC Max: {formatPercent(summaryStats.maxAuc)}</Badge>
              <Badge variant='light' color='red.3' className={brut.badge}>RootBrier Avg: {formatPercent(summaryStats.averageRootBrier)}</Badge>
              <Badge variant='light' color='red.3' className={brut.badge}>RootBrier Min: {formatPercent(summaryStats.minRootBrier)}</Badge>
            </Group>
          )}
        </>
      ) : (
        <CalibrationPlot calibrationData={calibrationData} visibilityBreakpoint={visibilityBreakpoint} />
      )}
    </Paper>
  );
}

export default ModelHistoryMobileView;
