// For input for MatchTable

import { CompletedMatch, LiveMatchData, PredictionResponse } from "../contracts";
import { UseFormReturnType } from "@mantine/form";

export type MatchData = CompletedMatch | LiveMatchData;

export type MatchStatus = 'Live' | 'Completed';

export interface MatchFilterOptions {
    teamName?: string;
    patchNumber?: string;
    heroIds?: number[];
    leagueId?: number;
    matchStatus?: MatchStatus;
}


// For DraftContext
export interface ActiveSlot {
    team: 'radiantTeam' | 'direTeam';
    index: number;
}

export interface FormValues {
    radiantTeam: (null | number)[];
    direTeam: (null | number)[];
    activeSlot: null | ActiveSlot;
}

export interface DraftContextType {
    form: UseFormReturnType<FormValues>;
    handleHeroPick: (heroId: number) => void;
    handleRemoveHero: (slot: ActiveSlot) => void;
    handleSubmit: (values: FormValues) => Promise<PredictionResponse | null>;
}


// HeroIcon props
export interface HeroIconProps {
    hero_id: number;
    hero_name: string;
    minHeight: number;
    minWidth: number;
}


export interface SelectableHeroProps extends HeroIconProps {
    isPicked?: boolean;
    canPick?: boolean;
    handlePick: (heroId: number) => void;
}

export interface DraftSlotProps {
    heroId: number | null;
    isActive: boolean;
    onClick: () => void;
    visibilityBreakpoint?: string;
}


export type TableRowDataProps = {
    tournamentName: string;
    formattedTime: string;
    formattedDate: string;
    radiantTeamName: string;
    radiantHeroes: number[];
    direTeamName: string;
    direHeroes: number[];
    predictedWinner: 'Radiant' | 'Dire' | null;
    actualWinner: 'Radiant' | 'Dire' | null;
    isCorrectPrediction: boolean | null;
    visibilityBreakpoint?: string;
};
