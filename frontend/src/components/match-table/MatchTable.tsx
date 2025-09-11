'use client';
import {Stack} from '@mantine/core'
import type { MatchData } from '@/types/domain';
import TableRow from './TableRow';
import TableHeader from './TableHeader';

export default function MatchTable({matchData}: {matchData: MatchData[]}) {
    return (
        <Stack w='100%' h='auto'>
            <TableHeader />
            {/* Table Body */}
            <Stack >
                {matchData.map((match: MatchData) => (
                    <TableRow key={match.match_id} matchData={match} />
                ))}
            </Stack>
        </Stack>
    )
}
