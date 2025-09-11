import { useState, useEffect } from 'react';
import type { LiveMatchData, LiveStateUpdateRequest } from '@/types/contracts/index';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';

export default function useSSEStream() : LiveMatchData[] {
    const [data, setData] = useState<LiveMatchData[]>([]);

    useEffect(() => {
        const eventSource = new EventSource(`${API_BASE_URL}/streaming/sse/live_matches`);

        // Log when SSE connection opens
        eventSource.onopen = () => {
            console.log(`[SSE] connected at ${new Date().toISOString()} (readyState=${eventSource.readyState})`);
        };

        eventSource.onmessage = (event) => {
            try {
                const notification: LiveStateUpdateRequest = JSON.parse(event.data);
                const list_matches: LiveMatchData[] = notification.live_matches
                console.log(`SSE received ${list_matches.length} live matches at ${new Date().toISOString()}`);
                setData(list_matches);
            } catch (error) {
                console.error("Error parsing SSE event data:", error);
                return;
            }
        };

        // Event listener for errors
        eventSource.onerror = (error) => {
            if (document.hidden) {
                console.log("Likely network suspension due to hidden pages");
                return;
            }

            else if (eventSource.readyState === EventSource.CONNECTING) {
                console.warn("SSE connection is reconnecting...");
            }

            else {
                console.error(`SSE connection was closed by the server: ${error}`);
                eventSource.close();
            }

        };

        return () => {
            eventSource.close();
        };
    }, []);

    return data;

};
