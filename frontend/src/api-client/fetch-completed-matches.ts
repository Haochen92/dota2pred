import { PaginatedMatchesResponse, MatchListFilters } from "@/types/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';

const fetchCompletedMatches = async (filters: MatchListFilters): Promise<PaginatedMatchesResponse> => {
  const basePath = `${API_BASE_URL}/matches/`;
  const q = new URLSearchParams();

  // Basic pagination
  if (filters?.offset !== undefined && filters.offset !== null) q.set('offset', String(filters.offset));
  if (filters?.limit !== undefined && filters.limit !== null) q.set('limit', String(filters.limit));

  // Optional scalar filters
  if (filters?.match_id !== undefined && filters.match_id !== null) q.set('match_id', String(filters.match_id));
  if (filters?.team_name) q.set('team_name', filters.team_name);
  if (filters?.patch_number) q.set('patch_number', filters.patch_number);
  if (filters?.patch_start_time) q.set('patch_start_time', filters.patch_start_time);
  if (filters?.patch_end_time) q.set('patch_end_time', filters.patch_end_time);

  // Array filters
  const heroIds = filters?.["hero_ids[]"];
  if (Array.isArray(heroIds)) {
    heroIds.forEach((id) => q.append('hero_ids[]', String(id)));
  }

  const teamIds = filters?.['team_ids[]'];
  if (Array.isArray(teamIds)) {
    teamIds.forEach((id) => q.append('team_ids[]', String(id)));
  }

  if (filters?.league_id !== undefined && filters.league_id !== null) q.set('league_id', String(filters.league_id));

  const fullUrl = `${basePath}?${q.toString()}`;
  const res = await fetch(fullUrl, { method: 'GET', headers: { 'Accept': 'application/json' } });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch matches: ${res.status} ${res.statusText} ${text}`);
  }
  const data = (await res.json()) as PaginatedMatchesResponse;
  return data;
};

export default fetchCompletedMatches;
