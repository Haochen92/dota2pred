'use client';

import { useState } from 'react';
import { Group, Button, Loader, Stack, Title} from '@mantine/core';
import { useMutation } from '@tanstack/react-query';

import useDraftContext from '@/hooks/useDraftContext';

import type { PredictionResponse } from '@/types/contracts';
import type { FormValues } from '@/types/domain';

import { TextLgMedium, TextSmMedium } from '@/components/typography/TextVariants';
import { IconRestore, IconSparkles } from '@tabler/icons-react';

export default function PredictionPanel() {
    const { form, handleSubmit } = useDraftContext();
    const [prediction, setPrediction] = useState<boolean | null>(null);



    const mutation = useMutation<PredictionResponse | null, Error, FormValues>({
        mutationFn: handleSubmit,
        onSuccess: (data) => {
            if (data && data.prediction !== undefined) {
                setPrediction(data.prediction);
            } else {
                setPrediction(null);
            }
        },
        onError: (error) => {
            console.error("Prediction failed:", error);
            setPrediction(null);
        }
    });

    const handleClick = async () => {
        mutation.mutate(form.values);
    };

    const renderPredictionResult = () => {
        if (mutation.isPending) {
            return <Loader size="xl" type='dots'/>;
        }
        if (prediction === null) {
            return null;
        }
        return (
            <>
                <Title visibleFrom='sm' order={1} c={ prediction ? 'green.2' : 'red.2'}>{prediction ? 'Radiant Victory' : 'Dire Victory'}</Title>
                <Title hiddenFrom='sm' order={6} ta='center' c={ prediction ? 'green.2' : 'red.2'}>{prediction ? 'Radiant Victory' : 'Dire Victory'}</Title>
            </>
        );
    };

    const handleReset = () => {
        setPrediction(null);
        form.reset();
    }

    return (
    <>
        <Stack visibleFrom='sm' px={12}>
            {/* Desktop View */}
            <Group w={300} justify='flex-start'>
            <Button
                flex={1}
                justify='space-around'
                onClick={handleClick} disabled={!form.isValid() || mutation.isPending} bg='gray.7' radius='md'
                leftSection={<IconSparkles size={18}/>}
            >
                <TextLgMedium>Predict</TextLgMedium>
            </Button>
            <Button flex={1} justify='space-around' onClick={handleReset} bg='gray.7' radius='md' disabled={mutation.isPending} leftSection={<IconRestore size={18}/>}>
                <TextLgMedium>Reset</TextLgMedium>
            </Button>
            </Group>
            <Group w='100%' justify='center' mt='md'>
                {renderPredictionResult()}
            </Group>
        </Stack>
        <Stack hiddenFrom='sm' px={8} w='70%'>
            {/* Mobile View */}
            <Group>
                <Button
                flex={1}
                justify='flex-start'
                onClick={handleClick} disabled={!form.isValid() || mutation.isPending} bg='gray.7' radius='md'
                leftSection={<IconSparkles size={18}/>}
                >
                    <TextSmMedium>Predict</TextSmMedium>
                </Button>
                <Button flex={1} justify='flex-start' onClick={handleReset} bg='gray.7' radius='md' disabled={mutation.isPending} leftSection={<IconRestore size={18}/>}>
                    <TextSmMedium>Reset</TextSmMedium>
                </Button>
            </Group>
            <Group w='100%' justify='center' mt='md'>
                {renderPredictionResult()}
            </Group>
        </Stack>
    </>


    )
}
