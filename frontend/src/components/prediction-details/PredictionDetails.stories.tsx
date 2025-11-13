import React from "react";
import PredictionDetailsView from "./PredictionDetailsView";
import type { PredictionDetailsViewProps } from "@/types/domain";

const mockPrediction: PredictionDetailsViewProps = {
    mode: 'mobile',
    predictedRadiantWin: true,
    prob: 0.60,
    teamPerformanceAdvantage: 0.2,
    teamHeadToHead: 0.58,
    playerHeroMasteryAdvantage: - 0.1,
    heroDraftAdvantage: 0.35,
};

export const Mobile = ({viewProps}: {viewProps: PredictionDetailsViewProps}) => <PredictionDetailsView viewProps={viewProps} />;
Mobile.args = {
    viewProps: mockPrediction,
};

export const Desktop = ({viewProps}: {viewProps: PredictionDetailsViewProps}) => <PredictionDetailsView viewProps={viewProps} />;
Desktop.args = {
    viewProps: {...mockPrediction, mode: 'modal'},
};
