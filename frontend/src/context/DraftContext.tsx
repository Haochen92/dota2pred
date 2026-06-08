import { createContext, useContext, useCallback, useMemo } from "react";
import { useForm } from "@mantine/form";
import type { DraftContextType, FormValues, ActiveSlot } from "@/types/domain";
import type { PredictionResponse } from "@/types/contracts";
import fetchDraftPrediction from "@/api-client/fetch-draft-prediction";

export const DraftContext = createContext<DraftContextType | null>(null);

export function DraftProvider({children}: {children: React.ReactNode}) {

    const form = useForm<FormValues>({
        mode: 'controlled', // Explicitly set mode to 'controlled' as UI needs to rerender on every change
        initialValues: {
            radiantTeam: [null, null, null, null, null] ,
            direTeam: [null, null, null, null, null],
            activeSlot: null
        },
        validate: {
            radiantTeam: (value) => value.includes(null) ? 'Select 5 heroes for Radiant' : null,
            direTeam: (value) => value.includes(null) ? 'Select 5 heroes for Dire' : null,
        }
    });

    const handleHeroPick = useCallback(( heroId: number ) => {
        const { activeSlot } = form.values;
        if (!activeSlot) return;

        const { team, index } = activeSlot;
        const valueKey = `${team}.${index}`; // Mantine's useForm parses .paths e.g. radiantTeam.0 for values

        // Append the hero to the correct team at the specified index
        form.setFieldValue(valueKey, heroId);

        // Auto advance to the next slot, using modulo to wrap around
        const teamArray = form.values[team];
        const nextIndex = (index + 1) % teamArray.length;

        if (teamArray[nextIndex] === null) {
            form.setFieldValue('activeSlot', { team, index: nextIndex });
        } else {
            // If the next slot is already filled, clear activeSlot
            form.setFieldValue('activeSlot', null);
        }
    }, [form]);


    const handleRemoveHero = useCallback((slot: ActiveSlot)  => {
        if (!slot) return; // Safety check for null activeSlot
        const { team, index } = slot;
        const valueKey = `${team}.${index}`;

        form.setFieldValue(valueKey, null);
    }, [form]);

    const handleSubmit = useCallback(async (values: FormValues) : Promise<PredictionResponse | null> => {
        try {
            const prediction = await fetchDraftPrediction(values);
            return prediction;
        } catch (error) {
            console.error("Error fetching prediction:", error);
            return null;
        }
    }, []);

    const value = useMemo(
        () => ({ form, handleHeroPick, handleRemoveHero, handleSubmit }),
        [form, handleHeroPick, handleRemoveHero, handleSubmit]
    );

    return (
        <DraftContext.Provider value={value}>
            {children}
        </DraftContext.Provider>
    );
}
