import type { components, operations } from "./api";

// Types generated from OpenAPI schema

// For the paginated matches endpoint
export type PaginatedMatchesResponse = components['schemas']['PaginatedMatchResponse'];
export type CompletedMatch = components['schemas']['CompletedMatchAPIPayload'];
export type MatchListFilters = operations['get_matches_matches__get']['parameters']['query'];

// For the public prediction endpoint
export type PredictionRequest = components['schemas']['PublicMatchPredictionRequest'];
export type PredictionResponse = components['schemas']['PublicMatchPredictionResponse'];


/// for model history endpoint
export type ModelHistoryResponse = components['schemas']['ModelHistoryResponse'];
export type ModelPerformanceEntry = components['schemas']['ModelPerformanceEntry'];
export type ModelHistoryRequest = operations['get_model_history_inference_model_history_get']['parameters']['query'];
export type HistoryRange = components['schemas']['HistoryRange'];
export type AggregateBy = components['schemas']['AggregateBy'];


// For the live match SSE updates
export type LiveStateUpdateRequest = components['schemas']['LiveStateUpdateRequest'];
export type LiveMatchData = components['schemas']['MatchNotifcationAPIPayload'];

// For hero image data
export type HeroImageData = components['schemas']['HeroImageData'];
export type HeroImageResponse = components['schemas']['HeroImageResponse'];


// For league data
export type LeagueDataResponse = components['schemas']['LeagueDataResponse'];
export type LeagueData = components['schemas']['dota_oracle_common__models__api__schema__LeagueData'];
