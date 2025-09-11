'use client';

import { useMemo, useEffect } from 'react';
import useSWR from 'swr';
import fetchCompletedMatches from '@/api/fetch-completed-matches';

// Hooks
import useSSEStream from '@/hooks/useSSEStream';
import { useFilterState } from './useFilterState';
import { useConstantsStore } from './useConstantsStore';

// Typings
import type { LiveMatchData, PaginatedMatchesResponse } from '@/types/contracts'
import type { MatchData } from '@/types/domain';

export default function useMatchTableData() {
    const { page, pageSize, filters} = useFilterState();
    const liveMatchData: LiveMatchData[] = useSSEStream();
    const { patches, hasFetched, fetchConstants } = useConstantsStore();

    // Ensure constants (patches, heroes, leagues) are fetched on mount
    useEffect(() => {
        if (!hasFetched) void fetchConstants();
    }, [hasFetched, fetchConstants]);

    // derive filtered liveMatchData to determine how many live matches for current page

    const filteredLiveMatches = useMemo(() => {
        // If matchStatus filter is 'Completed', return empty array as no live matches should be shown
        if (filters.matchStatus === 'Completed') return [];
    return liveMatchData.filter(match => {
            // Apply filtering logic based on filters
            if (filters.teamName) {
                const teamName = filters.teamName.toLowerCase();
                const radiantTeam = match.radiant_name?.toLowerCase() || '';
                const direTeam = match.dire_name?.toLowerCase() || '';
                if (!radiantTeam.includes(teamName) && !direTeam.includes(teamName)) {
                    return false;
                }
            }

            const latestPatch = patches[0] || undefined;
            // Live games are always on latest patch; only filter if a patch filter is explicitly set
            if (filters.patchNumber && filters.patchNumber !== latestPatch) {
                return false;
            }

            if (filters.leagueId) {
                const leagueId = match.leagueid || null;
                if (leagueId !== filters.leagueId) {
                    return false;
                }
            }
            if (filters.heroIds && filters.heroIds.length > 0){
                const heroFilterIdsSet = new Set(filters.heroIds);

                // use keyof to notify TypeScript about the keys of LiveMatchData
                const heroIdKeysToCheck: (keyof LiveMatchData)[] = [
                    'slot_0_hero_id', 'slot_1_hero_id', 'slot_2_hero_id',
                    'slot_3_hero_id', 'slot_4_hero_id', 'slot_128_hero_id',
                    'slot_129_hero_id', 'slot_130_hero_id', 'slot_131_hero_id',
                    'slot_132_hero_id'
                ];
                const hasMatchingHero = heroIdKeysToCheck.some(key =>
                    heroFilterIdsSet.has(match[key] as number)
                );

                if (!hasMatchingHero) {
                    return false;
                }
            }

            // Return match if all filters pass
            return true;
        })}, [liveMatchData, filters, patches]);

    // Dynamically calculate offset and limit based on pageSize and number of filtered live matches
    const filteredLiveMatchCount = filteredLiveMatches.length;
    const universalOffset = (page - 1) * pageSize;
    const liveMatchesCurrentPage = Math.min(Math.max(0, filteredLiveMatchCount - universalOffset), pageSize); // Clamp number of max matches to display to pageSize
    const completedMatchesLimit = pageSize - liveMatchesCurrentPage
    const completedMatchesOffset = Math.max(0, universalOffset - filteredLiveMatchCount)

    // fetch completed matches

    const emptyResponse: PaginatedMatchesResponse = { matches: [], total_count: 0, total_pages: 1 };
    const liveMatchesOnly = filters.matchStatus === 'Live' || completedMatchesLimit === 0;

    // Create a stable SWR key
    const swrKey = liveMatchesOnly
        ? null // Do not fetch completed matches if only live matches are requested
        : ['matches', completedMatchesOffset, completedMatchesLimit, filters];

    const { data , error: completedError, isLoading, mutate } = useSWR(
        swrKey,
        () => {
            // Map UI filters (camelCase) to API params (snake_case)
            const params: any = {}
            if (filters.teamName) params['team_name'] = filters.teamName;
            if (filters.patchNumber) params['patch_number'] = filters.patchNumber;
            if (filters.leagueId) params['league_id'] = filters.leagueId;
            if (filters.heroIds && filters.heroIds.length > 0) {
                params['hero_ids[]'] = filters.heroIds
            }
            // Use dynamic offset and limit for pagination
            params['offset'] = completedMatchesOffset;
            params['limit'] = completedMatchesLimit;
            return fetchCompletedMatches(params)

    },  { revalidateOnFocus: true, revalidateOnReconnect: true, refreshInterval: 0 })


    const completedRes = data ?? emptyResponse;

    // Event-driven revalidation: Reconcile polling and SSE updates
    useEffect(() => {
        if (!liveMatchesOnly) void mutate();
    }, [liveMatchesOnly, liveMatchData, mutate]);

    // combine live matches and completed matches for current page
    const matchTableData: MatchData[] = useMemo(() => {
    // Slice the live matches
        const liveMatchesForPage = filteredLiveMatches.slice(
            universalOffset,
            universalOffset + pageSize
        );

        const completedMatches = completedRes?.matches ?? [];
        return [...liveMatchesForPage, ...completedMatches].slice(0, pageSize);
    }, [filteredLiveMatches, completedRes, universalOffset, pageSize]);

    const totalPages = Math.ceil((filteredLiveMatchCount + (completedRes?.total_count ?? 0)) / pageSize) || 1;

    return { matchTableData, completedError, isLoading, totalPages };

}
