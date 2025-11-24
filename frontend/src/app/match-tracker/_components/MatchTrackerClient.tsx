'use client';

import { Suspense } from 'react';
import { Container, Stack, Title, Notification } from '@mantine/core';

// Child Components
import FiltersBar from '@/components/match-filter/FiltersBar';
import MatchTable from '@/components/match-table/MatchTable';
import TablePagination from '@/components/match-table/TablePagination';

// Loading and Error UI
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import { MatchTableSkeleton } from './MatchTableSkeleton';

// Hooks
import { useFilterState } from '@/hooks/useFilterState';
import useMatchTableData from '@/hooks/useMatchTableData';

export default function MatchTrackerClient() {
  const { page, filters, handlePageChange, handleFiltersChange } = useFilterState();
  const { matchTableData, totalPages, completedError, isValidating } = useMatchTableData();

  return (
    <Container size={1280} c="white" pl={0} pr={0}>
      <Stack align="stretch" gap="md" pt={16}>
        <Title order={4}>Match Tracker</Title>

        {/* The filter bar controls the shared filter state. */}
        <FiltersBar
          filterValues={filters}
          onChange={handleFiltersChange}
        />
        <ErrorBoundary>
          <Suspense fallback={<MatchTableSkeleton />}>
            {/* Render error, loading state, or the match table */}
            {
              completedError ? (
                <Notification title="Something went wrong" mb="md" color='red'>
                  Unable to load match data. Please try again.
                </Notification>
              ) : isValidating ? (
                <MatchTableSkeleton />
              ) : (
                <MatchTable matchData={matchTableData} />
              )
            }
            {/* The pagination component controls the shared page state. */}
            {
              !completedError && (
                <TablePagination
                  page={page}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              )
            }
          </Suspense>
        </ErrorBoundary>
      </Stack>
    </Container>
  );
}
