"use client";

import { Paper, Stack, Group, SegmentedControl, Chip, Table, ScrollArea, Badge, Divider } from '@mantine/core';
import type { HistoryRange, CalibrationPlotPoint } from '@/types/contracts';
import { dateFormatter } from '@/utils/date-formatter';
import { TextMdBold } from '@/components/typography/TextVariants';
import CalibrationPlot from './CalibrationPlot';

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
      bg='transparent'
      id='history-range-control-mobile'
      value={historyRange.toString()}
      data={historyRangeOptions}
      onChange={onHistoryRangeChange}
      radius={10}
      styles={(theme) => ({
        indicator: { backgroundColor: theme.colors.gray[9] },
        root: { gap: theme.spacing.xs },
        label: { color: theme.colors.gray[0] }
      })}
      withItemsBorders={false}
      transitionDuration={150}
      transitionTimingFunction='linear'
    />
  );

  const MetricsControl = () => (
    <Chip.Group multiple value={selectedMetrics} onChange={onSelectedMetricsChange}>
      <Group gap={8} wrap='wrap'>
        {chartMetricsData.map(metric => (
          <Chip key={metric.name} value={metric.name} color={metric.color} size='xs'>
            {metric.name}
          </Chip>
        ))}
      </Group>
    </Chip.Group>
  );

  const DataDisplayControl = () => (
    <SegmentedControl
      bg='transparent'
      id='data-display-control-mobile'
      value={dataDisplayOption}
      data={[
        { label: 'History', value: 'history' },
        { label: 'Calibration', value: 'calibration' },
      ]}
      onChange={handleDisplayOptionChange}
      radius={10}
      styles={(theme) => ({
        indicator: { backgroundColor: theme.colors.gray[9] },
        root: { gap: theme.spacing.xs },
        label: { color: theme.colors.gray[0] }
      })}
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
      p='xl'
      shadow='sm'
      component={Stack}
      w='100%'
      h='auto'
      bg='gray.7'
      gap='lg'
      style={{ borderRadius: 0 }}
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
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {historyData.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={visibleMetrics.length + 1} style={{ textAlign: 'center', opacity: 0.6 }}>
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
              <Badge variant='light' color='blue.3' radius='sm'>Accu Avg: {formatPercent(summaryStats.averageAccuracy)}</Badge>
              <Badge variant='light' color='blue.3' radius='sm'>Accu Max: {formatPercent(summaryStats.maxAccuracy)}</Badge>
              <Badge variant='light' color='green.3' radius='sm'>AUC Avg: {formatPercent(summaryStats.averageAuc)}</Badge>
              <Badge variant='light' color='green.3' radius='sm'>AUC Max: {formatPercent(summaryStats.maxAuc)}</Badge>
              <Badge variant='light' color='red.3' radius='sm'>RootBrier Avg: {formatPercent(summaryStats.averageRootBrier)}</Badge>
              <Badge variant='light' color='red.3' radius='sm'>RootBrier Min: {formatPercent(summaryStats.minRootBrier)}</Badge>
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
