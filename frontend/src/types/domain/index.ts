// For input for MatchTable

import type { CompletedMatch, LiveMatchData, PredictionResponse } from "../contracts";
import type { UseFormReturnType } from "@mantine/form";

export type MatchData = CompletedMatch | LiveMatchData;

export type MatchStatus = 'Live' | 'Completed';

export interface MatchFilterOptions {
    teamName?: string;
    patchNumber?: string;
    heroIds?: number[];
    leagueId?: number;
    matchStatus?: MatchStatus;
}


/** Global pointer for the current selected activeslot in the draft UI */
export interface ActiveSlot {
    /** which team the current active slot belongs to */
    team: 'radiantTeam' | 'direTeam';
    /** index number of slot in the team's draft array (0-4) */
    index: number;
}

export interface FormValues {
    radiantTeam: (null | number)[];
    direTeam: (null | number)[];
    /** Currently selected slot in the draft UI (or `null` when none is selected). */
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
    matchId: number;
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

export type PredictionDetailsContentProps = {
    matchId: number;
    mode: 'modal' | 'mobile';
};

// View props for presentation components
export type PredictionDetailsViewProps = {
  mode: 'modal' | 'mobile';
  predictedRadiantWin: boolean | null;
  prob: number | null; // 0–1
  teamPerformanceAdvantage: number | null;
  teamHeadToHead: number | null;
  playerHeroMasteryAdvantage: number | null;
  heroDraftAdvantage: number | null;
};
