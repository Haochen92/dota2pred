'use client';

import { parseISO, format, isToday } from 'date-fns';
import type { MatchData } from '@/types/domain';
import { extractHeroPicks } from '@/utils/extract-hero-picks';
import { TableRowDataProps } from '@/types/domain';
import TableRowView from './row-view/TableRowView';
import TableCardView from './card-view/TableCardView';

type TableRowProps = {
    matchData: MatchData;
};


export default function TableRow({ matchData }: TableRowProps) {

    const startTime = parseISO(matchData.start_time);
    const tournamentName = matchData.league_data?.name || 'Tournament';

    // Format time to be like "4:32 PM"
    const formattedTime = format(startTime, 'p');
    const formattedDate = isToday(startTime) ? 'Today' : format(startTime, 'MMM dd, yyyy');
    const heroPicks = extractHeroPicks(matchData);

    // predicted_outcome: true for Radiant, false for Dire
    const isPredicted = matchData.predicted_outcome !== null;
    const predictedWinner = isPredicted ? ( matchData.predicted_outcome === false ? 'Dire' : 'Radiant' ): null;

    const isCompleted = 'radiant_win' in matchData;
    const actualWinner = isCompleted ? (matchData.radiant_win ? 'Radiant' : 'Dire') : null;
    const isCorrectPrediction = isCompleted && isPredicted ? predictedWinner === actualWinner : null;

    const viewProps: TableRowDataProps = {
        matchId: matchData.match_id,
        tournamentName,
        formattedTime,
        formattedDate,
        radiantTeamName: matchData.radiant_name || 'Radiant',
        radiantHeroes: heroPicks.radiant,
        direTeamName: matchData.dire_name || 'Dire',
        direHeroes: heroPicks.dire,
        predictedWinner,
        actualWinner,
        isCorrectPrediction,
        visibilityBreakpoint:'sm'
    };

    return (
        <>
            <TableRowView {...viewProps} />
            <TableCardView {...viewProps} />
        </>
    )
}
