// Temporary types until API schema is regenerated
interface LeagueData {
    leagueid: number;
    tier?: string | null;
    name?: string | null;
}

interface LeagueDataResponse {
    leagues: LeagueData[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api'

export default async function fetchLeagueInfo(): Promise<LeagueData[]> {
    const endpointUrl = `${API_BASE_URL}/leagues/get_league_info`
    const res = await fetch(endpointUrl, { next: { revalidate: 3600 * 24 }})
    if (!res.ok) {
        throw new Error('Failed to fetch league data')
    }
    const data: LeagueDataResponse = await res.json()
    return data.leagues
}
