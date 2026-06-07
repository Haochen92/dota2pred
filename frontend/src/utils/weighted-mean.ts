import type { ModelPerformanceEntry } from '@/types/contracts';

/**
 * Match-count-weighted mean of a metric across model-performance buckets.
 *
 * Weighting by `match_count` makes the result performance *per match* — a
 * low-volume bucket can't swing the headline — and is invariant to how the
 * window is bucketed: Σ(value·count) / Σ(count) === total / matches regardless
 * of the `aggregate_by` granularity. That invariance is what keeps the NavBar
 * figure identical to the Model History card over the same range.
 *
 * Returns 0 when there are no matches.
 */
export function weightedMean(
    entries: ModelPerformanceEntry[],
    pick: (e: ModelPerformanceEntry) => number,
): number {
    const totalMatches = entries.reduce((sum, e) => sum + (e.match_count ?? 0), 0);
    if (totalMatches <= 0) return 0;
    return entries.reduce((sum, e) => sum + pick(e) * (e.match_count ?? 0), 0) / totalMatches;
}
