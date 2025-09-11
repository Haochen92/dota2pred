import { Suspense } from "react";
import MatchTrackerClient from "./_components/MatchTrackerClient";

export default function MatchTrackerPage() {
  return (
    <Suspense fallback={<div />}>
      <MatchTrackerClient />
    </Suspense>
  );
}
