import type { FormValues } from "@/types/domain";
import type { PredictionRequest, PredictionResponse } from "@/types/contracts";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';

// Type guard to ensure all hero slots are filled
const isTeamComplete = (team: (number | null)[]): team is number[] => {
    return !team.includes(null);
};


const fetchDraftPrediction = async (draftData: FormValues): Promise<PredictionResponse> => {
    const { radiantTeam, direTeam } = draftData;

    // Ensure all hero slots are filled
    if (!isTeamComplete(radiantTeam) || !isTeamComplete(direTeam)) {
        throw new Error("All hero slots must be filled before fetching prediction.");
    }

    // Construct the payload (array-based per OpenAPI schema)
    const PredictionRequestPayload: PredictionRequest = {
        radiant_heroes: radiantTeam as number[],
        dire_heroes: direTeam as number[],
    };

    const minDelayPromise = new Promise(resolve => setTimeout(resolve, 500)); // Minimum delay of 500ms for UX
    const fetchPromise = fetch(`${API_BASE_URL}/inference/predict`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        body: JSON.stringify(PredictionRequestPayload),
    });

    const [response] = await Promise.all([fetchPromise, minDelayPromise]);

    if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(`Failed to fetch prediction: ${response.status} ${response.statusText} ${text}`);
    }

    const predictionData: PredictionResponse = await response.json()
    return predictionData;
}

export default fetchDraftPrediction;
