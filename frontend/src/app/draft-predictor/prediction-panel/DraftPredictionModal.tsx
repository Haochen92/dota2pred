import { Modal, Stack, Group, Box, Progress, Divider, ThemeIcon } from "@mantine/core";
import { IconTrophy } from "@tabler/icons-react";
import {
    TextLgBold,
    TextSmRegular,
    TextSmMedium,
} from "@/components/typography/TextVariants";
import classes from "./prediction-panel.module.css";

export type DraftPredictionModalProps = {
    opened: boolean;
    onClose: () => void;
    prediction: boolean | null;
    probability: number | null;
};

export default function DraftPredictionModal({
    opened,
    onClose,
    prediction,
    probability,
}: DraftPredictionModalProps) {
    const predictedRadiantWin = prediction === true;
    const hasResult = prediction != null;

    const winnerLabel = !hasResult
        ? "—"
        : predictedRadiantWin
          ? "Radiant Victory"
          : "Dire Victory";

    // `probability` is P(Radiant win); derive each side's share for the split bar.
    const radiantPct = probability != null ? Math.round(100 * probability) : 0;
    const direPct = probability != null ? 100 - radiantPct : 0;
    const confidence = !hasResult
        ? null
        : predictedRadiantWin
          ? radiantPct
          : direPct;

    // Team-driven accent. Fills (border/bar) use .4; text uses .2 — matching
    // the Match Tracker convention (filled badges = .4, text labels = .2).
    const accentColor = !hasResult
        ? "var(--mantine-color-gray-5)"
        : predictedRadiantWin
          ? "var(--mantine-color-green-4)"
          : "var(--mantine-color-red-4)";
    const winnerTextColor = !hasResult
        ? "var(--mantine-color-gray-3)"
        : predictedRadiantWin
          ? "var(--mantine-color-green-2)"
          : "var(--mantine-color-red-2)";
    const accentGlow = !hasResult
        ? "transparent"
        : predictedRadiantWin
          ? "rgba(87, 207, 68, 0.45)"
          : "rgba(248, 82, 59, 0.45)";

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            centered
            size={380}
            overlayProps={{ blur: 4, backgroundOpacity: 0.6 }}
            withCloseButton={false}
            padding={0}
            radius={10}
        >
            <Box
                className={classes.modalBody}
                p="lg"
                bg="gray.8"
                style={
                    {
                        "--accent-color": accentColor,
                        "--accent-glow": accentGlow,
                    } as React.CSSProperties
                }
            >
                <Stack gap="md">
                    <div className={classes.accentBar} />

                    <TextSmMedium c="gray.3" tt="uppercase" style={{ letterSpacing: 1 }}>
                        Predicted Winner
                    </TextSmMedium>

                    <Group justify="space-between" align="center" wrap="nowrap">
                        <Group gap="sm" wrap="nowrap">
                            <ThemeIcon
                                size={44}
                                radius="md"
                                variant="light"
                                color={predictedRadiantWin ? "green" : "red"}
                            >
                                <IconTrophy size={24} />
                            </ThemeIcon>
                            <TextLgBold c={winnerTextColor}>{winnerLabel}</TextLgBold>
                        </Group>

                        <Stack gap={0} align="flex-end">
                            <TextLgBold c="gray.0" style={{ fontSize: 28, lineHeight: 1.1 }}>
                                {confidence != null ? `${confidence}%` : "N/A"}
                            </TextLgBold>
                            <TextSmRegular c="gray.4">confidence</TextSmRegular>
                        </Stack>
                    </Group>

                    {/* Radiant vs Dire probability split */}
                    <Stack gap={6}>
                        <Group justify="space-between">
                            <TextSmMedium c="green.2">Radiant {radiantPct}%</TextSmMedium>
                            <TextSmMedium c="red.2">Dire {direPct}%</TextSmMedium>
                        </Group>
                        <Progress.Root size="xl" radius="xl" aria-label="Predicted win probability">
                            <Progress.Section value={radiantPct} color="green.4" />
                            <Progress.Section value={direPct} color="red.4" />
                        </Progress.Root>
                    </Stack>

                    <Divider color="gray.6" />

                    <TextSmRegular c="gray.4">
                        Confidence reflects the model&rsquo;s estimated probability for the
                        predicted winner given the current draft.
                    </TextSmRegular>
                </Stack>
            </Box>
        </Modal>
    );
}
