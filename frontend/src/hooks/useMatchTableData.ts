'use client';

import { useMemo, useEffect } from 'react';
import useSWR from 'swr';
import fetchCompletedMatches from '@/api-client/fetch-completed-matches';

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

    // Stable key
    const swrKey: [string, number, number, typeof filters] = ['matches', completedMatchesOffset, completedMatchesLimit, filters];

    // Abstracted fetcher respecting live mode & pagination
    const fetchCompletedFetcher = async ([, offset, limit, filt]: typeof swrKey): Promise<PaginatedMatchesResponse> => {
        if (filt.matchStatus === 'Live' || limit === 0) return emptyResponse; // live-only: no completed data
        const params: any = {};
        if (filt.teamName) params['team_name'] = filt.teamName;
        if (filt.patchNumber) params['patch_number'] = filt.patchNumber;
        if (filt.leagueId) params['league_id'] = filt.leagueId;
        if (filt.heroIds && filt.heroIds.length > 0) params['hero_ids[]'] = filt.heroIds;
        params['offset'] = offset;
        params['limit'] = limit;
        return fetchCompletedMatches(params);
    };

    const { data , error: completedError, isValidating } = useSWR(
        swrKey,
        fetchCompletedFetcher,
        { revalidateOnFocus: true, revalidateOnReconnect: true, refreshInterval: 0, keepPreviousData: true, fallbackData: emptyResponse }
    );

    const completedRes = data || emptyResponse;

    // combine live matches and completed matches for current page
    const matchTableData: MatchData[] = useMemo(() => {
        // Slice the live matches
        const liveMatchesForPage = filteredLiveMatches.slice(
            universalOffset,
            universalOffset + pageSize
        );

        if (filters.matchStatus === 'Live') return liveMatchesForPage; // ignore completed cache entirely in live mode

        const completedMatches = completedRes.matches ?? [];
        const combined = [...liveMatchesForPage, ...completedMatches];

        // Deduplicate by match_id while preserving order (live first)
        const seen = new Set<number>();
        const deduped: MatchData[] = [];
        for (const m of combined) {
            const id = (m as any).match_id as number;
            if (!seen.has(id)) {
                seen.add(id);
                deduped.push(m);
            }
        }

        return deduped.slice(0, pageSize);
    }, [filteredLiveMatches, completedRes, universalOffset, pageSize, filters.matchStatus]);

    const totalPages = Math.ceil((filteredLiveMatchCount + (completedRes?.total_count ?? 0)) / pageSize) || 1;

    return { matchTableData, completedError, isValidating, totalPages };

}
