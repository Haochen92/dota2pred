import type { components, operations } from "./api";

// For the paginated matches endpoint
export type PaginatedMatchesResponse = components['schemas']['PaginatedMatchResponse'];
export type CompletedMatch = components['schemas']['CompletedMatchAPIPayload'];
export type MatchListFilters = operations['get_matches_matches__get']['parameters']['query'];

// For the public prediction endpoint
export type PredictionRequest = components['schemas']['PublicMatchPredictionRequest'];
export type PredictionResponse = components['schemas']['PublicMatchPredictionResponse'];

// For the live match SSE updates
export type LiveStateUpdateRequest = components['schemas']['LiveStateUpdateRequest'];
export type LiveMatchData = components['schemas']['MatchNotifcationAPIPayload'];

// For hero image data
export type HeroImageData = components['schemas']['HeroImageData'];
export type HeroImageResponse = components['schemas']['HeroImageResponse'];

