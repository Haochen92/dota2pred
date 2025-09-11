// For input for MatchTable

import { CompletedMatch, LiveMatchData } from "../contracts";

export type MatchData = CompletedMatch | LiveMatchData;

export type MatchStatus = 'Live' | 'Completed';

export interface MatchFilterOptions {
    teamName?: string;
    patchNumber?: string;
    heroIds?: number[];
    leagueId?: number;
    matchStatus?: MatchStatus;
}
