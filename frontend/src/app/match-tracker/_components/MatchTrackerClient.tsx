'use client';

import { Suspense } from 'react';
import { Container, Stack, Title } from '@mantine/core';

// Child Components
import FiltersBar from '@/components/match-filter/FiltersBar';
import MatchTable from '@/components/match-table/MatchTable';
import TablePagination from '@/components/match-table/TablePagination';

// Hooks
import { useFilterState } from '@/hooks/useFilterState';
import useMatchTableData from '@/hooks/useMatchTableData';

export default function MatchTrackerClient() {
  const { page, filters, handlePageChange, handleFiltersChange } = useFilterState();
  const { matchTableData, totalPages, completedError, isLoading } = useMatchTableData();

  return (
    <Container size={1280} c="white" pl={0} pr={0}>
      <Stack align="stretch" gap="md" pt={16}>
        <Title order={4}>Match Tracker</Title>

        {/* The filter bar controls the shared filter state. */}
        <FiltersBar
          filterValues={filters}
          onChange={handleFiltersChange}
        />

        {/* The main content area, wrapped in Suspense for client-side data fetching. */}
        <Suspense fallback={<div>Loading Matches...</div>}>

          {/* Render error, loading state, or the match table */}
          {completedError && <div>Error loading completed matches: {String(completedError)}</div>}

          {isLoading
            ? <div>Loading...</div>
            : <MatchTable matchData={matchTableData} />
          }

          {/* The pagination component controls the shared page state. */}
          <TablePagination
            page={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </Suspense>

      </Stack>
    </Container>
  );
}
