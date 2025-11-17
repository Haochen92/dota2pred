import { Modal, Title, Stack, Group, Badge, Progress, Divider } from "@mantine/core";
import { TextLgMedium, TextMdMedium } from "@/components/typography/TextVariants";

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
    const winnerLabel = prediction == null ? '—' : predictedRadiantWin ? 'Radiant Victory' : 'Dire Victory';
    const winnerColor = prediction == null ? 'gray' : predictedRadiantWin ? 'green.3' : 'red.3';
    const percent = probability != null
        ? Math.round(100 * (predictedRadiantWin ? probability : 1 - probability))
        : null;

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            centered
            size="auto"
            overlayProps={{ blur: 4, backgroundOpacity: 0.55 }}
            withCloseButton={false}
            padding={8}
        >
            <Stack gap="md" p="sm" bg='gray.7'>
                <Title order={3} c="gray.0">Prediction Result</Title>

                <Group justify="space-between" align="center">
                    <Badge color={winnerColor} variant="filled" size="lg">
                        {winnerLabel}
                    </Badge>
                    <TextLgMedium c="gray.1">
                        Confidence: {percent != null ? `${percent}%` : 'N/A'}
                    </TextLgMedium>
                </Group>

                <Progress
                    value={percent ?? 0}
                    color={winnerColor}
                    size="xl"
                    radius="xl"
                    aria-label="Predicted win probability"
                />

                <Divider my="xs" />
                <TextMdMedium size="xs" c="gray.3">
                    This probability reflects the model’s confidence in the predicted winner for the current draft.
                </TextMdMedium>
            </Stack>
        </Modal>
    );
}
