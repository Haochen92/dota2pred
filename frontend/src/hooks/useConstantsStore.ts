import { create } from "zustand";
import { HeroImageData } from "@/types/contracts";
import fetchHeroData from "@/api-client/fetch-hero-data";
import fetchPatchData from "@/api-client/fetch-patch-data";
import fetchLeagueInfo from "@/api-client/fetch-league-info";

// Temporary types until API schema is regenerated
interface LeagueData {
    leagueid: number;
    tier?: string | null;
    name?: string | null;
}

interface DotaConstantsState {
    heroes: HeroImageData[];
    patches: string[];
    leagues: LeagueData[];
    isLoading: boolean;
    hasFetched: boolean;
    error: Error | null;
    tournamentNameToIdMap: Map<string, number>;
    tournamentIdToNameMap: Map<number, string>;
    heroNameToIdMap: Map<string, number>;
    idToHeroNameMap: Map<number, string>;
    fetchConstants: () => Promise<void>;
}

export const useConstantsStore = create<DotaConstantsState>((set, get) => ({
    heroes: [],
    patches: [],
    leagues: [],

    tournamentNameToIdMap: new Map<string, number>(),
    tournamentIdToNameMap: new Map<number, string>(),
    heroNameToIdMap: new Map<string, number>(),
    idToHeroNameMap: new Map<number, string>(),

    isLoading: false,
    hasFetched: false,
    error: null,

    fetchConstants: async () => {
        const { hasFetched, isLoading } = get();
        if (hasFetched || isLoading) return;

        set({ isLoading: true, error: null });
        try {
            const [heroDataArray, patchIds, leagueDataArray] = await Promise.all([
                fetchHeroData(),
                fetchPatchData(),
                fetchLeagueInfo(),
            ]);

            const newTournamentNameToIdMap = new Map<string, number>();
            const newTournamentIdToNameMap = new Map<number, string>();
            leagueDataArray.forEach(league => {
                if (league.name) {
                    newTournamentNameToIdMap.set(league.name, league.leagueid);
                    newTournamentIdToNameMap.set(league.leagueid, league.name);
                }
            });

            const newHeroNameToIdMap = new Map<string, number>();
            const newIdToHeroNameMap = new Map<number, string>();
            heroDataArray.forEach(hero => {
                newHeroNameToIdMap.set(hero.hero_name, hero.hero_id);
                newIdToHeroNameMap.set(hero.hero_id, hero.hero_name);
            });

            set({
                heroes: heroDataArray,
                patches: patchIds,
                leagues: leagueDataArray,
                tournamentNameToIdMap: newTournamentNameToIdMap,
                tournamentIdToNameMap: newTournamentIdToNameMap,
                heroNameToIdMap: newHeroNameToIdMap,
                idToHeroNameMap: newIdToHeroNameMap,
                isLoading: false,
                hasFetched: true,
            });
        } catch (error: any) {
            console.error("Failed to fetch Dota constants:", error);
            set({ error, isLoading: false, hasFetched: false });
        }
    },
}));
