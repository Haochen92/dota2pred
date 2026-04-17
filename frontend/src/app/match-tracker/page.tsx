import { Suspense } from 'react';
import MatchTrackerClient from "./_components/MatchTrackerClient";
import { MatchTableSkeleton } from './_components/MatchTableSkeleton';

// Wrap client component that uses useSearchParams in a Suspense boundary
// to satisfy Next.js requirement for prerendering.
export default function MatchTrackerPage() {
  return (
    <Suspense fallback={<MatchTableSkeleton />}>
      <MatchTrackerClient />
    </Suspense>
  );
}
