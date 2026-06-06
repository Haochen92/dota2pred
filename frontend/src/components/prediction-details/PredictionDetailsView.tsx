import type { PredictionDetailsViewProps } from "@/types/domain";
import { Badge, Group, Stack, Box } from "@mantine/core";
import { pctFormatter } from "@/utils/features-formatter";
import {
  TextSmMedium,
  TextSmBold,
  TextSmRegular,
  TextMdBold,
} from "@/components/typography/TextVariants";
import brut from "@/styles/brutalist.module.css";

type Factor = { label: string; value: number | null };

/** One diverging "tug of war" bar: green to the right = Radiant edge,
 *  red to the left = Dire edge. Length is relative to the strongest factor. */
function FactorBar({ label, value, maxAbs }: Factor & { maxAbs: number }) {
  const hasVal = value != null;
  const isRadiant = (value ?? 0) >= 0;
  const frac = hasVal ? Math.min(Math.abs(value as number) / maxAbs, 1) : 0;
  const fillPct = frac * 50; // half the track at most
  const color = isRadiant
    ? "var(--mantine-color-green-4)"
    : "var(--mantine-color-red-4)";

  return (
    <Stack gap={6} w="100%">
      <Group justify="space-between" align="center" wrap="nowrap">
        <TextSmMedium c="gray.2">{label}</TextSmMedium>
        <TextSmBold c={hasVal ? (isRadiant ? "green.2" : "red.2") : "gray.5"}>
          {hasVal ? pctFormatter(value) : "N/A"}
        </TextSmBold>
      </Group>
      <Box className={brut.factorTrack}>
        <Box className={brut.factorCenter} />
        {hasVal && (
          <Box
            className={brut.factorFill}
            style={{
              width: `${fillPct}%`,
              background: color,
              ...(isRadiant ? { left: "50%" } : { right: "50%" }),
            }}
          />
        )}
      </Box>
    </Stack>
  );
}

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

  const winner = predictedRadiantWin ? "Radiant" : "Dire";
  const winnerColor = predictedRadiantWin ? "green" : "red";
  const isMobile = mode === "mobile";

  // matchup is a 0..1 probability; recentre it on 0 like the other diffs.
  const normalizedHeadToHead = teamHeadToHead != null ? teamHeadToHead - 0.5 : null;

  const factors: Factor[] = [
    { label: "Team Performance", value: teamPerformanceAdvantage },
    { label: "Team Head-to-Head", value: normalizedHeadToHead },
    { label: "Player Hero Mastery", value: playerHeroMasteryAdvantage },
    { label: "Hero Draft", value: heroDraftAdvantage },
  ];

  // Normalise bar lengths to the strongest factor so small edges stay visible.
  const maxAbs = Math.max(
    1e-6,
    ...factors.map((f) => (f.value != null ? Math.abs(f.value) : 0)),
  );

  const winPercentage = prob != null ? (predictedRadiantWin ? prob : 1 - prob) : null;
  const formattedWinPercentage = winPercentage != null ? pctFormatter(winPercentage) : "N/A";

  return (
    <Stack gap="md" p="md" w="100%" maw={isMobile ? undefined : 720} mx="auto">
      {/* Predicted winner + confidence */}
      <Group justify="space-between" align="center" wrap="nowrap">
        <TextMdBold c={`${winnerColor}.2`} tt="uppercase" style={{ letterSpacing: 1 }}>
          {winner} favoured
        </TextMdBold>
        <Badge className={brut.badge} variant="filled" size="lg" bg={`${winnerColor}.4`} c="white">
          {formattedWinPercentage}
        </Badge>
      </Group>

      {/* Per-factor diverging bars */}
      <Stack gap="sm">
        {factors.map((f) => (
          <FactorBar key={f.label} label={f.label} value={f.value} maxAbs={maxAbs} />
        ))}
      </Stack>

      {/* Direction legend */}
      <Group justify="space-between" align="center" wrap="nowrap" w="100%">
        <TextSmRegular c="red.2">◄ Dire edge</TextSmRegular>
        {!isMobile && <TextSmRegular c="gray.2">bar length = relative strength</TextSmRegular>}
        <TextSmRegular c="green.2">Radiant edge ►</TextSmRegular>
      </Group>
    </Stack>
  );
}
