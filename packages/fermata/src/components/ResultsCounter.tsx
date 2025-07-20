import type { ResultsCounterProps } from '../types';

export function ResultsCounter({ filteredCount, totalCount, hasActiveFilters }: ResultsCounterProps) {
  if (!hasActiveFilters && filteredCount === totalCount) {
    return null; // Don't show counter when no filters are active
  }

  return (
    <div className="results-counter">
      Showing {filteredCount} of {totalCount} recordings
    </div>
  );
} 