import { Suspense } from 'react';
import MatchTrackerClient from "./_components/MatchTrackerClient";
import { MatchTableSkeleton } from './_components/MatchTableSkeleton';

export const metadata = {
  title: 'Match Tracker',
  description: 'Live and recent Dota 2 pro matches with model win-probability predictions.',
};

// Wrap client component that uses useSearchParams in a Suspense boundary
// to satisfy Next.js requirement for prerendering.
export default function MatchTrackerPage() {
  return (
    <Suspense fallback={<MatchTableSkeleton />}>
      <MatchTrackerClient />
    </Suspense>
  );
}
