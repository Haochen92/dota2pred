'use client';

import { useState } from 'react';
import { Group, Button, Loader, Box, Notification } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useMutation } from '@tanstack/react-query';

import useDraftContext from '@/hooks/useDraftContext';

import type { PredictionResponse } from '@/types/contracts';
import type { FormValues } from '@/types/domain';

import { TextSmBold, TextSmMedium } from '@/components/typography/TextVariants';
import { IconRestore, IconSparkles } from '@tabler/icons-react';

import DraftPredictionModal from './DraftPredictionModal';
import classes from '../draft-predictor.module.css';

type ButtonsProps = {
    onPredict: () => void;
    onReset: () => void;
    predictDisabled: boolean;
    resetDisabled: boolean;
    pending: boolean;
    full?: boolean;
};

function ActionButtons({ onPredict, onReset, predictDisabled, resetDisabled, pending, full }: ButtonsProps) {
    return (
        <Group gap="sm" wrap="nowrap" w={full ? '100%' : undefined}>
            <Button
                className={`${classes.btn} ${classes.btnPredict}`}
                flex={full ? 2 : undefined}
                onClick={onPredict}
                disabled={predictDisabled}
                bg="blue.4"
                c="gray.9"
                radius={8}
                size="md"
                leftSection={pending ? <Loader size={16} color="gray.9" type="dots" /> : <IconSparkles size={18} stroke={2.5} />}
            >
                {pending ? 'Predicting' : 'Predict'}
            </Button>
            <Button
                className={classes.btn}
                flex={full ? 1 : undefined}
                onClick={onReset}
                disabled={resetDisabled}
                bg="gray.7"
                c="gray.1"
                radius={8}
                size="md"
                leftSection={<IconRestore size={18} stroke={2.5} />}
            >
                Reset
            </Button>
        </Group>
    );
}

export default function PredictionPanel() {
    const { form, handleSubmit } = useDraftContext();
    const [opened, { close, open }] = useDisclosure(false);
    const [prediction, setPrediction] = useState<boolean | null>(null);
    const [probability, setProbability] = useState<number | null>(null);

    const mutation = useMutation<PredictionResponse | null, Error, FormValues>({
        mutationFn: handleSubmit,
        onSuccess: (data) => {
            if (data && data.prediction !== undefined) {
                setPrediction(data.prediction);
                setProbability(data.probability ?? null);
                open();
            } else {
                setPrediction(null);
                setProbability(null);
            }
        },
        onError: (error) => {
            console.error('Prediction failed:', error);
            setPrediction(null);
            setProbability(null);
        },
    });

    const handleClick = async () => {
        close();
        mutation.mutate(form.values);
    };

    const handleReset = () => {
        setPrediction(null);
        setProbability(null);
        close();
        form.reset();
    };

    // --- Derive a human-readable status for the command bar -----------------
    const { radiantTeam, direTeam, activeSlot } = form.values;
    const radiantCount = radiantTeam.filter((h) => h !== null).length;
    const direCount = direTeam.filter((h) => h !== null).length;
    const isComplete = radiantCount === 5 && direCount === 5;

    let statusText: string;
    let dotColor: string;
    if (mutation.isPending) {
        statusText = 'Running the model…';
        dotColor = 'var(--mantine-color-blue-4)';
    } else if (isComplete) {
        statusText = 'Draft complete — hit Predict';
        dotColor = 'var(--mantine-color-blue-4)';
    } else if (activeSlot) {
        const t = activeSlot.team === 'radiantTeam' ? 'Radiant' : 'Dire';
        statusText = `Picking ${t} · slot ${activeSlot.index + 1} — choose a hero`;
        dotColor = activeSlot.team === 'radiantTeam' ? 'var(--mantine-color-green-4)' : 'var(--mantine-color-red-4)';
    } else {
        statusText = 'Select a slot, then choose a hero';
        dotColor = 'var(--mantine-color-gray-4)';
    }

    const predictDisabled = !form.isValid() || mutation.isPending;

    return (
        <>
            <DraftPredictionModal
                opened={opened}
                onClose={close}
                prediction={prediction}
                probability={probability}
            />

            {mutation.isError && (
                <Notification title="Something went wrong" mb="md" color="red" onClose={() => mutation.reset()}>
                    Unable to get prediction. Please try again.
                </Notification>
            )}

            {/* Desktop command bar */}
            <Box className={classes.commandBar} visibleFrom="sm">
                <Group gap={10} wrap="nowrap" miw={0}>
                    <span className={classes.statusDot} style={{ backgroundColor: dotColor }} />
                    <TextSmMedium c="gray.2" style={{ letterSpacing: 0.3 }}>
                        {statusText}
                    </TextSmMedium>
                </Group>
                <ActionButtons
                    onPredict={handleClick}
                    onReset={handleReset}
                    predictDisabled={predictDisabled}
                    resetDisabled={mutation.isPending}
                    pending={mutation.isPending}
                />
            </Box>

            {/* Mobile sticky action bar */}
            <Box className={classes.mobileBar} hiddenFrom="sm">
                <Group gap={8} wrap="nowrap" mb={10} justify="center">
                    <span className={classes.statusDot} style={{ backgroundColor: dotColor }} />
                    <TextSmBold c="gray.2">{statusText}</TextSmBold>
                </Group>
                <ActionButtons
                    full
                    onPredict={handleClick}
                    onReset={handleReset}
                    predictDisabled={predictDisabled}
                    resetDisabled={mutation.isPending}
                    pending={mutation.isPending}
                />
            </Box>
        </>
    );
}
