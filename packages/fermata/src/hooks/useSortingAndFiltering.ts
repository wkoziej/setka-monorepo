import { useState, useEffect, useMemo } from 'react';
import type { Recording, FilterConfig, SortOption, RecordingStatus } from '../types';

const DEFAULT_FILTERS: FilterConfig = {
  searchTerm: '',
  status: 'all',
  sortOption: 'date-desc'
};

const STORAGE_KEY = 'fermata-filters-v1';

// Utility functions
function getTotalSize(recording: Recording): number {
  return Object.values(recording.file_sizes).reduce((sum, size) => sum + size, 0);
}

function getStatusPriority(status: RecordingStatus): number {
  if (typeof status === 'object' && 'Failed' in status) {
    return 0;
  }
  
  const statusPriority: Record<string, number> = {
    'Failed': 0,
    'Recorded': 1,
    'Extracted': 2,
    'Analyzed': 3,
    'SetupRendered': 4,
    'Rendered': 5,
    'Uploaded': 6
  };
  
  return statusPriority[status] || 0;
}

// Sorting functions
const sortingFunctions: Record<SortOption, (a: Recording, b: Recording) => number> = {
  'date-desc': (a, b) => b.last_updated - a.last_updated,
  'date-asc': (a, b) => a.last_updated - b.last_updated,
  'name-asc': (a, b) => a.name.localeCompare(b.name),
  'name-desc': (a, b) => b.name.localeCompare(a.name),
  'size-desc': (a, b) => getTotalSize(b) - getTotalSize(a),
  'size-asc': (a, b) => getTotalSize(a) - getTotalSize(b),
  'status': (a, b) => getStatusPriority(a.status) - getStatusPriority(b.status)
};

// Filtering functions
function applyFilters(recordings: Recording[], filterConfig: FilterConfig): Recording[] {
  let filtered = recordings;
  
  // Search filter
  if (filterConfig.searchTerm) {
    const searchTerm = filterConfig.searchTerm.toLowerCase();
    filtered = filtered.filter(recording =>
      recording.name.toLowerCase().includes(searchTerm)
    );
  }
  
  // Status filter
  if (filterConfig.status !== 'all') {
    filtered = filtered.filter(recording => {
      if (typeof filterConfig.status === 'object' && 'Failed' in filterConfig.status) {
        return typeof recording.status === 'object' && 'Failed' in recording.status;
      }
      return recording.status === filterConfig.status;
    });
  }
  
  return filtered;
}

function applySorting(recordings: Recording[], sortOption: SortOption): Recording[] {
  const sortFunction = sortingFunctions[sortOption];
  return [...recordings].sort(sortFunction);
}

// Load from localStorage with error handling
function loadFiltersFromStorage(): FilterConfig {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // Validate parsed data has required fields
      if (parsed && typeof parsed === 'object' && 
          'searchTerm' in parsed && 'status' in parsed && 'sortOption' in parsed) {
        return { ...DEFAULT_FILTERS, ...parsed };
      }
    }
  } catch (error) {
    console.warn('Failed to load filters from localStorage:', error);
  }
  return DEFAULT_FILTERS;
}

// Save to localStorage with error handling
function saveFiltersToStorage(filters: FilterConfig): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  } catch (error) {
    console.warn('Failed to save filters to localStorage:', error);
  }
}

export function useSortingAndFiltering(recordings: Recording[]) {
  const [filterConfig, setFilterConfig] = useState<FilterConfig>(() => 
    loadFiltersFromStorage()
  );

  // Save to localStorage whenever filterConfig changes
  useEffect(() => {
    saveFiltersToStorage(filterConfig);
  }, [filterConfig]);

  // Process recordings (filter + sort)
  const processedRecordings = useMemo(() => {
    const filtered = applyFilters(recordings, filterConfig);
    const sorted = applySorting(filtered, filterConfig.sortOption);
    return sorted;
  }, [recordings, filterConfig]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return filterConfig.searchTerm !== '' || filterConfig.status !== 'all';
  }, [filterConfig.searchTerm, filterConfig.status]);

  // Update filter function
  const updateFilter = (key: keyof FilterConfig, value: any) => {
    setFilterConfig(prev => ({ ...prev, [key]: value }));
  };

  // Clear filters function (preserve sort option)
  const clearFilters = () => {
    setFilterConfig(prev => ({ 
      ...DEFAULT_FILTERS, 
      sortOption: prev.sortOption 
    }));
  };

  return {
    processedRecordings,
    filterConfig,
    hasActiveFilters,
    updateFilter,
    clearFilters
  };
} 