'use client';
import {Stack, Table} from '@mantine/core'
import { LiveMatchData } from '@/types/contracts/index';
import TableRow from './TableRow';
import TableHeader from './TableHeader';
import TableFooter from './TablePagination';


export default function MatchTable({matchData}: {matchData: LiveMatchData[]}) {
    return (
        <Stack w='100%' h='auto'>
            <TableHeader />
            {/* Table Body */}
            <Stack >
                {matchData.map((match: LiveMatchData) => (
                    <TableRow key={match.match_id} matchData={match} />
                ))}
            </Stack>
            {/* <TableFooter /> */}
        </Stack>
    )
}
