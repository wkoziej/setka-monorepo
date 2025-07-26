# Specyfikacja: Sortowanie i Filtrowanie w fermata

## Cel

Implementacja funkcjonalności sortowania i filtrowania w card-based layout fermata dla lepszej organizacji i wyszukiwania danych.

## Analiza Obecnej Architektury

### Struktura Danych
```typescript
interface Recording {
  name: string;           // Nazwa nagrania
  path: string;          // Ścieżka do pliku
  status: RecordingStatus; // Status przetwarzania
  last_updated: number;   // Unix timestamp
  file_sizes: Record<string, number>; // Rozmiary plików
}
```

### Obecny Layout
- ✅ Card-based design z responsive layout
- ✅ Hook `useRecordings()` centralizuje dane
- ✅ TypeScript types są zdefiniowane
- ✅ Design system z CSS custom properties
- ❌ Brak sortowania UI i logiki
- ❌ Brak filtrowania UI i logiki

### Layout Change: Cards vs Table
Przechodzmy z table-based sortowania (clicking headers) na controls-based approach lepiej pasujący do card layout.

## Wymagania Funkcjonalne

### F1. Jednolity Color Scheme
**F1.1 Button Colors**
- Wszystkie przyciski używają `btn-primary` (niebieski)
- Wyjątek: Delete button zachowuje `btn-danger` (czerwony) dla bezpieczeństwa
- Success green (zielony) tylko dla status indicators

### F2. Controls Bar nad Cards

**F2.1 Layout Struktury**
```
[Header - fermata + actions]
[Controls Bar - sort + search + filter]  ← NOWE
[Results Counter - "5 of 12 recordings"] ← NOWE
[Cards List]
```

**F2.2 Sort Dropdown**
- Label: "Sort by:"
- Options:
  - "Newest First" (default) - last_updated desc
  - "Oldest First" - last_updated asc
  - "By Status" - workflow priority order
  - "Name A→Z" - alphabetical asc
  - "Name Z→A" - alphabetical desc
  - "Largest First" - total file size desc
  - "Smallest First" - total file size asc

**F2.3 Search Box**
- Real-time search w nazwach nagrań
- Placeholder: "🔍 Search recordings..."
- Case-insensitive matching
- Debounced 300ms

**F2.4 Status Filter**
- Dropdown z opcjami statusów
- "All Statuses" (default)
- Individual statuses: Recorded, Extracted, Analyzed, Setup, Rendered, Uploaded, Failed

### F3. Results & Persistence

**F3.1 Results Counter**
- Format: "Showing X of Y recordings"
- Hidden gdy nie ma filtrów aktywnych
- Clear filters button gdy filtry aktywne

**F3.2 LocalStorage Persistence**
- Save/restore sort selection
- Save/restore search term
- Save/restore status filter
- Key: `fermata-filters-v1`

## Wymagania Techniczne

### Frontend State Management

**Updated hook: `useSortingAndFiltering`**
```typescript
type SortOption =
  | 'date-desc'    // Newest First (default)
  | 'date-asc'     // Oldest First
  | 'status'       // By Status
  | 'name-asc'     // Name A→Z
  | 'name-desc'    // Name Z→A
  | 'size-desc'    // Largest First
  | 'size-asc';    // Smallest First

interface FilterConfig {
  searchTerm: string;
  status: RecordingStatus | 'all';
  sortOption: SortOption;
}

const DEFAULT_FILTERS: FilterConfig = {
  searchTerm: '',
  status: 'all',
  sortOption: 'date-desc'
};
```

**Hook Implementation:**
```typescript
export function useSortingAndFiltering(recordings: Recording[]) {
  const [filterConfig, setFilterConfig] = useState<FilterConfig>(() => {
    // Load from localStorage
    const saved = localStorage.getItem('fermata-filters-v1');
    return saved ? { ...DEFAULT_FILTERS, ...JSON.parse(saved) } : DEFAULT_FILTERS;
  });

  // Save to localStorage on change
  useEffect(() => {
    localStorage.setItem('fermata-filters-v1', JSON.stringify(filterConfig));
  }, [filterConfig]);

  const processedRecordings = useMemo(() => {
    let filtered = applyFilters(recordings, filterConfig);
    let sorted = applySorting(filtered, filterConfig.sortOption);
    return sorted;
  }, [recordings, filterConfig]);

  const hasActiveFilters = filterConfig.searchTerm !== '' || filterConfig.status !== 'all';

  return {
    processedRecordings,
    filterConfig,
    hasActiveFilters,
    updateFilter: (key: keyof FilterConfig, value: any) =>
      setFilterConfig(prev => ({ ...prev, [key]: value })),
    clearFilters: () => setFilterConfig({ ...DEFAULT_FILTERS, sortOption: filterConfig.sortOption })
  };
}
```

### UI Components

**New Components:**
```typescript
// ControlsBar.tsx - sort + search + filter controls
interface ControlsBarProps {
  filterConfig: FilterConfig;
  onUpdateFilter: (key: keyof FilterConfig, value: any) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

// ResultsCounter.tsx - showing X of Y
interface ResultsCounterProps {
  filteredCount: number;
  totalCount: number;
  hasActiveFilters: boolean;
}
```

### Updated CSS Classes

**Controls styling:**
```css
.controls-bar {
  display: flex;
  gap: var(--spacing-4);
  align-items: center;
  padding: var(--spacing-4);
  background: white;
  border: 1px solid var(--gray-200);
  border-radius: var(--border-radius);
  margin-bottom: var(--spacing-4);
}

.controls-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.controls-group label {
  font-weight: 500;
  color: var(--gray-700);
  white-space: nowrap;
}

.search-input {
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--gray-300);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  min-width: 200px;
}

.filter-select {
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--gray-300);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  background: white;
}

.results-counter {
  color: var(--gray-600);
  font-size: 0.875rem;
  margin-bottom: var(--spacing-3);
}
```

### Sorting Logic

**Sort functions:**
```typescript
const sortingFunctions: Record<SortOption, (a: Recording, b: Recording) => number> = {
  'date-desc': (a, b) => b.last_updated - a.last_updated,
  'date-asc': (a, b) => a.last_updated - b.last_updated,
  'name-asc': (a, b) => a.name.localeCompare(b.name),
  'name-desc': (a, b) => b.name.localeCompare(a.name),
  'size-desc': (a, b) => getTotalSize(b) - getTotalSize(a),
  'size-asc': (a, b) => getTotalSize(a) - getTotalSize(b),
  'status': (a, b) => {
    const statusPriority = {
      'Failed': 0, 'Recorded': 1, 'Extracted': 2,
      'Analyzed': 3, 'SetupRendered': 4, 'Rendered': 5, 'Uploaded': 6
    };
    return getStatusPriority(a.status) - getStatusPriority(b.status);
  }
};
```

## Implementation Plan

### Phase 1: Button Color Fix (15 min)
1. ✅ Update all action buttons to `btn-primary`
2. ✅ Keep Delete as `btn-danger`
3. ✅ Test visual consistency

### Phase 2: Controls Bar (45 min)
1. ✅ Create `ControlsBar` component
2. ✅ Add sort dropdown with options
3. ✅ Add search input
4. ✅ Add status filter dropdown
5. ✅ Style with CSS classes

### Phase 3: Sorting Logic (30 min)
1. ✅ Create `useSortingAndFiltering` hook
2. ✅ Implement all sort functions
3. ✅ Integrate with RecordingList
4. ✅ Test all sort options

### Phase 4: Search & Filter (30 min)
1. ✅ Implement search filtering
2. ✅ Implement status filtering
3. ✅ Add debouncing for search
4. ✅ Test filter combinations

### Phase 5: Results Counter & Persistence (30 min)
1. ✅ Add ResultsCounter component
2. ✅ LocalStorage save/restore
3. ✅ Clear filters functionality
4. ✅ Final testing

**Total Estimated Time: 2.5 hours**

## TDD Test Cases

### Test 1: Button Colors
```typescript
// All action buttons should be btn-primary except delete
expect(viewButton).toHaveClass('btn-primary');
expect(playButton).toHaveClass('btn-primary');
expect(deleteButton).toHaveClass('btn-danger');
```

### Test 2: Sort Options
```typescript
// Should have all 7 sort options
expect(sortDropdown).toHaveOptions([
  'Newest First', 'Oldest First', 'By Status',
  'Name A→Z', 'Name Z→A', 'Largest First', 'Smallest First'
]);
```

### Test 3: Search Filtering
```typescript
// Should filter recordings by name
const recordings = [{ name: 'test-video' }, { name: 'other-recording' }];
userEvent.type(searchInput, 'test');
expect(screen.getByText('test-video')).toBeInTheDocument();
expect(screen.queryByText('other-recording')).not.toBeInTheDocument();
```

### Test 4: LocalStorage Persistence
```typescript
// Should save and restore filter state
userEvent.selectOptions(sortDropdown, 'name-asc');
userEvent.type(searchInput, 'my-search');
// Reload component
expect(sortDropdown).toHaveValue('name-asc');
expect(searchInput).toHaveValue('my-search');
```
