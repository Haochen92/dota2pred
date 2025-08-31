'use client'

import {Container} from '@mantine/core'
import useSSEStream from '@/hooks/useSSEStream'
import { LiveMatchData } from '@/types/contracts/index';
import MatchTable from './_components/MatchTable';

export default function MatchesClient() {

    const liveMatchData: LiveMatchData[] = useSSEStream();

    return(
        <Container size={1280} c='white'>
            <MatchTable matchData={liveMatchData} />
        </Container>
        
    )
}
