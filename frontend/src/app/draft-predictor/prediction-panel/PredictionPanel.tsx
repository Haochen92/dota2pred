'use client';

import { useState } from 'react';
import { Group, Button, Loader, Stack, UnstyledButton} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useMutation } from '@tanstack/react-query';

import useDraftContext from '@/hooks/useDraftContext';

import type { PredictionResponse } from '@/types/contracts';
import type { FormValues } from '@/types/domain';

import { TextLgMedium, TextSmMedium } from '@/components/typography/TextVariants';
import { IconRestore, IconSparkles } from '@tabler/icons-react';

import DraftPredictionModal from './DraftPredictionModal';

export default function PredictionPanel() {
    const { form, handleSubmit } = useDraftContext();
    const [ opened , { close, open }] = useDisclosure(false);
    const [prediction, setPrediction] = useState<boolean | null>(null);
    const [probability, setProbability] = useState<number | null>(null);



    const mutation = useMutation<PredictionResponse | null, Error, FormValues>({
        mutationFn: handleSubmit,
        onSuccess: (data) => {
            if (data && data.prediction !== undefined) {
                setPrediction(data.prediction);
                setProbability(data.probability ?? null);
                // Open modal after successful prediction
                open();
            } else {
                setPrediction(null);
                setProbability(null);
            }
        },
        onError: (error) => {
            console.error("Prediction failed:", error);
            setPrediction(null);
            setProbability(null);
        }
    });

    const handleClick = async () => {
        // Close any previous modal and trigger prediction
        close();
        mutation.mutate(form.values);
    };

    const handleReset = () => {
        setPrediction(null);
        setProbability(null);
        close();
        form.reset();
    }

    return (
    <>
        {/* Prediction result modal */}
        <DraftPredictionModal
            opened={opened}
            onClose={close}
            prediction={prediction}
            probability={probability}
        />

        <Stack visibleFrom='sm' px={12}>
            {/* Desktop View */}
            <Group w={300} justify='flex-start'>
            <Button
                flex={1}
                justify='space-around'
                onClick={handleClick} disabled={!form.isValid() || mutation.isPending} bg='gray.7' radius='md'
                rightSection={<IconSparkles size={18}/>}
                style={{'borderRadius': 16}}
            >
                <TextLgMedium>Predict</TextLgMedium>
            </Button>
            <Button
                flex={1}
                justify='space-around'
                onClick={handleReset} bg='gray.7' radius='md' disabled={mutation.isPending} rightSection={<IconRestore size={18}/>}
                style={{'borderRadius': 16}}
            >
                <TextLgMedium>Reset</TextLgMedium>
            </Button>
            </Group>
            <Group w='100%' justify='center' mt='md'>
                {mutation.isPending && <Loader size="xl" type='dots'/>}
            </Group>
        </Stack>
        <Stack hiddenFrom='sm' px={8} w='70%'>
            {/* Mobile View */}
            <Group>
                <Button
                    style={{'borderRadius': 16}}
                    flex={1}
                    justify='flex-start'
                    onClick={handleClick} disabled={!form.isValid() || mutation.isPending} bg='gray.7' radius='md'
                    rightSection={<IconSparkles size={18}/>}
                >
                    <TextSmMedium>Predict</TextSmMedium>
                </Button>
                <Button flex={1} justify='flex-start' style={{'borderRadius':16}} onClick={handleReset} bg='gray.7' radius='md' disabled={mutation.isPending} rightSection={<IconRestore size={18}/>}>
                    <TextSmMedium>Reset</TextSmMedium>
                </Button>
            </Group>
            <Group w='100%' justify='center' mt='md'>
                {mutation.isPending && <Loader size="xl" type='dots'/>}
            </Group>
        </Stack>
    </>


    )
}
