import React from 'react';
import type { ControlsBarProps, SortOption, RecordingStatus } from '../types';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'date-desc', label: 'Newest First' },
  { value: 'date-asc', label: 'Oldest First' },
  { value: 'status', label: 'By Status' },
  { value: 'name-asc', label: 'Name A→Z' },
  { value: 'name-desc', label: 'Name Z→A' },
  { value: 'size-desc', label: 'Largest First' },
  { value: 'size-asc', label: 'Smallest First' }
];

export function ControlsBar({
  filterConfig,
  onUpdateFilter,
  onClearFilters,
  hasActiveFilters
}: ControlsBarProps) {
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateFilter('searchTerm', event.target.value);
  };

  const handleSortChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    onUpdateFilter('sortOption', event.target.value as SortOption);
  };

  const handleStatusChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (value === 'failed') {
      onUpdateFilter('status', { Failed: '' });
    } else {
      onUpdateFilter('status', value);
    }
  };

  const getStatusValue = (status: RecordingStatus | 'all'): string => {
    if (typeof status === 'object' && 'Failed' in status) {
      return 'failed';
    }
    return status;
  };

  return (
    <div className="controls-bar">
      <div className="controls-group">
        <label htmlFor="sort-select">Sort by:</label>
        <select
          id="sort-select"
          className="filter-select"
          value={filterConfig.sortOption}
          onChange={handleSortChange}
        >
          {SORT_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="controls-group">
        <input
          type="search"
          className="search-input"
          placeholder="🔍 Search recordings..."
          value={filterConfig.searchTerm}
          onChange={handleSearchChange}
          aria-label="Search recordings"
        />
      </div>

      <div className="controls-group">
        <label htmlFor="status-select">Status:</label>
        <select
          id="status-select"
          className="filter-select"
          value={getStatusValue(filterConfig.status)}
          onChange={handleStatusChange}
        >
          <option value="all">All Statuses</option>
          <option value="Recorded">📹 Recorded</option>
          <option value="Extracted">📁 Extracted</option>
          <option value="Analyzed">📊 Analyzed</option>
          <option value="SetupRendered">🎬 Setup</option>
          <option value="Rendered">✅ Rendered</option>
          <option value="Uploaded">🚀 Uploaded</option>
          <option value="failed">❌ Failed</option>
        </select>
      </div>

      {hasActiveFilters && (
        <div className="controls-group">
          <button
            className="btn btn-secondary"
            onClick={onClearFilters}
          >
            Clear Filters
          </button>
        </div>
      )}
    </div>
  );
}
