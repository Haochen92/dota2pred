"use client";

import useSWR from "swr";
import fetchPredictionDetails from "@/api/fetch-prediction-details";
import type { PredictionDetailsRequest, PredictionDetailsResponse } from "@/types/contracts";
import type { PredictionDetailsViewProps, PredictionDetailsContentProps } from "@/types/domain";
import PredictionDetailsView from "./PredictionDetailsView";
import PredictionDetailsSkeleton from "./PredictionDetailsSkeleton";


function PredictionDetailsContent({ matchId, mode }: PredictionDetailsContentProps) {
    const fetcher = ({matchId}: {matchId: number}) => {
        const params: PredictionDetailsRequest = { match_id: matchId };
        return fetchPredictionDetails(params);
    };

    const { data, error, isLoading } = useSWR<PredictionDetailsResponse, Error>(
        {matchId},
        fetcher,
        { revalidateOnFocus: true, keepPreviousData: true }
    );

    if (isLoading) return <PredictionDetailsSkeleton mode={mode} />;
    if (error) return <PredictionDetailsSkeleton mode={mode} />;

    const predictionData = data?.prediction_details;
    const allFeatures = data?.features;

    const viewProps: PredictionDetailsViewProps = {
        mode: mode,
        predictedRadiantWin: predictionData?.prediction || null,
        prob: predictionData?.prediction_probability || null,
        teamPerformanceAdvantage: allFeatures?.radiant_dire_team_wr_diff || null,
        teamHeadToHead: allFeatures?.radiant_dire_matchup || null,
        playerHeroMasteryAdvantage: allFeatures?.radiant_dire_player_wr_diff || null,
        heroDraftAdvantage: allFeatures?.radiant_dire_hero_wr_diff || null,
    }

    return (
        <PredictionDetailsView viewProps={viewProps} />
    )

};

export default function PredictionDetailsClient({ matchId, mode }: PredictionDetailsContentProps) {
    return (
        <PredictionDetailsContent matchId={matchId} mode={mode} />
    );
}
