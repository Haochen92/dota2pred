import type { PredictionDetailsViewProps } from "@/types/domain";
import {
  Badge,
  Group,
  Tooltip,
  Stack,
  Text,
} from "@mantine/core";

import { BarChart } from "@mantine/charts";
import { pctFormatter } from "@/utils/features-formatter";


export default function PredictionDetailsView({ viewProps }: { viewProps: PredictionDetailsViewProps }) {
  const {
    mode,
    predictedRadiantWin,
    prob,
    teamPerformanceAdvantage,
    teamHeadToHead,
    playerHeroMasteryAdvantage,
    heroDraftAdvantage,
  } = viewProps;
  const winner = predictedRadiantWin ? 'Radiant' : 'Dire';
  const winnerColor = predictedRadiantWin != null && predictedRadiantWin ? 'green' : 'red';

  const normalizedHeadToHead = teamHeadToHead != null ? teamHeadToHead - 0.5 : null;

  const chartsData = [
    { feature: "Team Performance Advantage", probability: teamPerformanceAdvantage },
    { feature: "Team Head-to-Head", probability: normalizedHeadToHead },
    { feature: "Player Hero Mastery Advantage", probability: playerHeroMasteryAdvantage },
    { feature: "Hero Draft Advantage", probability: heroDraftAdvantage },
  ]

  const isMobile = mode === 'mobile';

  const chartSpecificProps = isMobile
    ? {
        orientation: 'vertical' as any,
        w: '100%',
        h: 200,
        yAxisProps: { domain: [-100, 100] },
        withXAxis: false,
        referenceLines: [{ x: 0 }],
      }
    : {
        orientation: 'horizontal' as any,
        w: '100%',
        h: 400,
        xAxisProps: { domain: [-100, 100] },
        withXAxis: true,
        referenceLines: [{ y: 0 }],
      };

  const Legend = () => (
    <Group gap="sm">
      <Group gap={6} align="center">
        <Tooltip
        label={'Radiant Advantage'}
        position="top"
        >
          <span aria-hidden style={{ width: 24, height: 24, borderRadius: 999, background: "var(--mantine-color-green-2)" }} />
        </Tooltip>
        <Text size="xs" c="white">Radiant +</Text>
      </Group>
      <Group gap={6} align="center">
        <Tooltip
        label={'Dire Advantage'}
        position="top"
        >
          <span aria-hidden style={{ width: 24, height: 24, borderRadius: 999, background: "var(--mantine-color-red-2)" }} />
        </Tooltip>
        <Text size="xs" c="white">Dire +</Text>
      </Group>
    </Group>
  );

  const winPercentage = prob != null ? (predictedRadiantWin ? prob : 1 - prob) : null;
  const formattedWinPercentage = winPercentage != null ? pctFormatter(winPercentage) : null;


  return (
    <Group p="md" justify="center" w="100%">
      <Stack justify="center" align='center' w={ mode === 'mobile' ? 300 : 800} p='sm'>
        <Group justify="space-between" align="center" mb="md" w='100%' px={ mode === 'mobile' ? 0 : 'md' } wrap='nowrap'>
          <Legend />
          <Tooltip
            label={`${winner} Win Probability`}
            position="top"
            withArrow
            events={{ hover: true, focus: true, touch: true }}
          >
            <Badge color={`${winnerColor}.2`} variant='filled' size='xl' c='white'>
              {formattedWinPercentage}
            </Badge>
          </Tooltip>
        </Group>
        <BarChart
          textColor="white"
          data={chartsData}
          dataKey="feature"
          series={[{ name: 'probability', color: 'blue.4' }]}
          getBarColor={(probability) => ( probability >= 0 ? 'green.2' : 'red.2')}
          valueFormatter={(value) => pctFormatter(value)}
          barProps={{ radius: 10, width: 20}}
          minBarSize={10}
          maxBarWidth={isMobile ? 30 : 80}
          strokeDasharray={0}
          tickLine="none"
          // gridAxis="none"
          withBarValueLabel
          {...chartSpecificProps}
        />
      </Stack>
    </Group>
  );
}
