"use client";

import { Paper, Stack, Group, Text, Table, ScrollArea, Skeleton } from "@mantine/core";
import { BarChart } from "@mantine/charts";
import type { CalibrationPlotPoint } from "@/types/contracts";
import { pctFormatter } from "@/utils/features-formatter";

export interface CalibrationPlotProps {
  calibrationData: CalibrationPlotPoint;
  title?: string;
  height?: number;
  width?: number | string;
  visibilityBreakpoint?: string;
}

export default function CalibrationPlot({
  calibrationData,
  title = "Calibration Plot",
  height = 360,
  width = "100%",
  visibilityBreakpoint,
}: CalibrationPlotProps) {
  const bins = calibrationData?.bins ?? [];

  const chartData = bins.map((b) => ({
    bin: b.bin_name,
    "avg accuracy": b.bin_accuracy,
    "avg confidence": b.average_confidence,
    match_count: b.match_count,
  }));

  const hasData = chartData.length > 0;

  return (
    <Paper
      p="md"
      shadow="sm"
      component={Stack}
      w={width}
      h="auto"
      bg="gray.7"
      style={{ borderRadius: 0 }}
      withBorder={true}
    >
      <Group justify="space-between" align="center">
        <Text c="gray.0" fw={600} size="sm">
          {title}
        </Text>
      </Group>

      {!hasData ? (
        <Stack gap="md" w="100%">
          {/* Desktop chart skeleton */}
          <Skeleton visibleFrom={visibilityBreakpoint} h={height} radius="md" />

          {/* Mobile table skeleton */}
          <Stack hiddenFrom={visibilityBreakpoint} gap="xs">
            <Skeleton h={20} w="60%" radius="sm" />
            {Array.from({ length: 5 }).map((_, index) => (
              <Group key={index} grow>
                <Skeleton h={16} radius="sm" />
                <Skeleton h={16} radius="sm" />
                <Skeleton h={16} radius="sm" />
                <Skeleton h={16} radius="sm" />
              </Group>
            ))}
          </Stack>
        </Stack>
      ) : (
        <>
          {/* Desktop chart */}
          <BarChart
            visibleFrom={visibilityBreakpoint}
            data={chartData}
            dataKey="bin"
            series={[
              { name: "avg confidence", color: "teal.3" },
              { name: "avg accuracy", color: "blue.3" },
            ]}
            h={height}
            w={width}
            yAxisProps={{ domain: [0, 1] }}
            valueFormatter={(v) => pctFormatter(v as number | null)}
            withBarValueLabel
            withLegend={true}
            minBarSize={10}
            barProps={{ radius: 8 }}
          />

          {/* Mobile simple table */}
          <ScrollArea w="100%" hiddenFrom={visibilityBreakpoint} type="hover">
            <Table
              highlightOnHover
              withTableBorder={false}
              withColumnBorders={false}
              verticalSpacing="xs"
              horizontalSpacing="md"
            >
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Bin</Table.Th>
                  <Table.Th>Avg Confidence</Table.Th>
                  <Table.Th>Avg Accuracy</Table.Th>
                  <Table.Th>Matches</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {chartData.map((row) => (
                  <Table.Tr key={row.bin}>
                    <Table.Td>{row.bin}</Table.Td>
                    <Table.Td>{pctFormatter(row["avg confidence"] as number | null)}</Table.Td>
                    <Table.Td>{pctFormatter(row["avg accuracy"] as number | null)}</Table.Td>
                    <Table.Td>{row.match_count}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        </>
      )}
    </Paper>
  );
}
