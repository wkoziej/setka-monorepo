# Specyfikacja: Sortowanie i Filtrowanie w fermata

## Cel

Implementacja funkcjonalności sortowania i filtrowania w tabeli nagrań fermata dla lepszej organizacji i wyszukiwania danych.

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

### Obecne Kolumny Tabeli
1. **Recording Name** - nazwa + rozmiar (sortowalne: alfabetycznie, rozmiar)
2. **Status** - status przetwarzania (filtrowalne: po statusie)
3. **Last Updated** - czas ostatniej modyfikacji (sortowalne: chronologicznie)
4. **Actions** - przyciski (nie sortowalne)

### Stan Obecny
- ✅ Tabela HTML z nagłówkami
- ✅ Hook `useRecordings()` centralizuje dane
- ✅ TypeScript types są zdefiniowane
- ❌ Brak sortowania UI i logiki
- ❌ Brak filtrowania UI i logiki

## Wymagania Funkcjonalne

### F1. Sortowanie Kolumn

**F1.1 Sortowanie przez Kliknięcie Nagłówka**
- Kliknięcie nagłówka kolumny zmienia sortowanie
- Pierwszy klik: ascending (A→Z, 0→9, oldest→newest)
- Drugi klik: descending (Z→A, 9→0, newest→oldest)
- Trzeci klik: reset do domyślnego sortowania

**F1.2 Wizualne Wskaźniki Sortowania**
- Ikona ↑ dla ascending
- Ikona ↓ dla descending
- Brak ikony dla unsorted
- Aktywna kolumna ma podświetlenie

**F1.3 Kolumny Sortowalne**
- **Recording Name**: alfabetycznie (A-Z)
- **Status**: priorytet statusów (Failed → Recorded → Extracted → Analyzed → Setup → Rendered → Uploaded)
- **Last Updated**: chronologicznie (newest first domyślnie)
- **File Size**: numerycznie (total size)

### F2. Filtrowanie Danych

**F2.1 Panel Filtrów**
- Umieszczony nad tabelą, pod nagłówkiem aplikacji
- Zwijany/rozwijany toggle button
- Przycisk "Clear All Filters"

**F2.2 Rodzaje Filtrów**

**Search Box (Recording Name)**
- Real-time search w nazwach nagrań
- Case-insensitive matching
- Placeholder: "Search recordings..."

**Status Filter**
- Dropdown z opcjami statusów
- "All Statuses" (default)
- Poszczególne statusy: Recorded, Extracted, Analyzed, etc.
- "Failed Only" (quick filter)

**Date Range Filter**
- "Last 24 hours"
- "Last 7 days" 
- "Last 30 days"
- "Custom range" (date picker)

**File Size Filter**
- "Small (< 1GB)"
- "Medium (1-5GB)" 
- "Large (> 5GB)"
- Custom range slider

### F3. Kombinacja Filtrów i Sortowania
- Sortowanie działające na przefiltrowanych danych
- Zachowanie sortowania po zmianie filtrów
- Licznik wyników: "Showing X of Y recordings"

## Wymagania Techniczne

### Frontend State Management

**Nowy hook: `useSortingAndFiltering`**
```typescript
interface SortConfig {
  column: SortableColumn;
  direction: 'asc' | 'desc' | null;
}

interface FilterConfig {
  searchTerm: string;
  status: RecordingStatus | 'all';
  dateRange: DateRange | null;
  sizeRange: SizeRange | null;
}

type SortableColumn = 'name' | 'status' | 'last_updated' | 'file_size';

interface DateRange {
  start: Date;
  end: Date;
}

interface SizeRange {
  min: number; // bytes
  max: number; // bytes
}
```

**Hook Implementation:**
```typescript
export function useSortingAndFiltering(recordings: Recording[]) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    column: 'last_updated',
    direction: 'desc' // newest first
  });
  
  const [filterConfig, setFilterConfig] = useState<FilterConfig>({
    searchTerm: '',
    status: 'all',
    dateRange: null,
    sizeRange: null
  });

  const processedRecordings = useMemo(() => {
    let filtered = applyFilters(recordings, filterConfig);
    let sorted = applySorting(filtered, sortConfig);
    return sorted;
  }, [recordings, sortConfig, filterConfig]);

  return {
    processedRecordings,
    sortConfig,
    filterConfig,
    setSortConfig,
    setFilterConfig,
    clearFilters: () => setFilterConfig(defaultFilters),
    toggleSort: (column: SortableColumn) => { /* toggle logic */ }
  };
}
```

### Komponenty UI

**Nowe Komponenty:**
```typescript
// FilterPanel.tsx - panel z wszystkimi filtrami
interface FilterPanelProps {
  filterConfig: FilterConfig;
  onFilterChange: (config: FilterConfig) => void;
  onClearFilters: () => void;
  isVisible: boolean;
  onToggleVisibility: () => void;
}

// SortableHeader.tsx - nagłówek kolumny z sortowaniem
interface SortableHeaderProps {
  column: SortableColumn;
  label: string;
  sortConfig: SortConfig;
  onSort: (column: SortableColumn) => void;
}

// RecordingCounter.tsx - licznik wyników
interface RecordingCounterProps {
  filteredCount: number;
  totalCount: number;
}
```

### Logika Sortowania

**Funkcje sortujące:**
```typescript
const sortingFunctions = {
  name: (a: Recording, b: Recording) => a.name.localeCompare(b.name),
  
  status: (a: Recording, b: Recording) => {
    const statusPriority = {
      'Failed': 0,
      'Recorded': 1,
      'Extracted': 2,
      'Analyzed': 3,
      'SetupRendered': 4,
      'Rendered': 5,
      'Uploaded': 6
    };
    return statusPriority[getStatusKey(a.status)] - statusPriority[getStatusKey(b.status)];
  },
  
  last_updated: (a: Recording, b: Recording) => a.last_updated - b.last_updated,
  
  file_size: (a: Recording, b: Recording) => {
    const sizeA = Object.values(a.file_sizes).reduce((sum, size) => sum + size, 0);
    const sizeB = Object.values(b.file_sizes).reduce((sum, size) => sum + size, 0);
    return sizeA - sizeB;
  }
};
```

### Logika Filtrowania

**Funkcje filtrujące:**
```typescript
const filteringFunctions = {
  searchTerm: (recordings: Recording[], term: string) =>
    recordings.filter(r => r.name.toLowerCase().includes(term.toLowerCase())),
    
  status: (recordings: Recording[], status: string) =>
    status === 'all' ? recordings : recordings.filter(r => getStatusKey(r.status) === status),
    
  dateRange: (recordings: Recording[], range: DateRange) =>
    recordings.filter(r => {
      const recordingDate = new Date(r.last_updated * 1000);
      return recordingDate >= range.start && recordingDate <= range.end;
    }),
    
  sizeRange: (recordings: Recording[], range: SizeRange) =>
    recordings.filter(r => {
      const totalSize = Object.values(r.file_sizes).reduce((sum, size) => sum + size, 0);
      return totalSize >= range.min && totalSize <= range.max;
    })
};
```

## Implementacja UI

### Layout Rozszerzony

```typescript
// Nowa struktura RecordingList
return (
  <div style={{ padding: '20px' }}>
    {/* Existing header */}
    <div style={{ ... }}>
      <h1>𝄐 fermata 𝄑</h1>
      <div>
        <button onClick={toggleFilters}>🔍 Filters</button>
        <button onClick={refreshRecordings}>Refresh</button>
        <button>Settings</button>
      </div>
    </div>

    {/* NEW: Filter Panel */}
    <FilterPanel 
      filterConfig={filterConfig}
      onFilterChange={setFilterConfig}
      onClearFilters={clearFilters}
      isVisible={filtersVisible}
      onToggleVisibility={setFiltersVisible}
    />

    {/* NEW: Results Counter */}
    <RecordingCounter 
      filteredCount={processedRecordings.length}
      totalCount={recordings.length}
    />

    {/* MODIFIED: Table with sortable headers */}
    <table>
      <thead>
        <tr>
          <SortableHeader column="name" label="Recording Name" {...sortProps} />
          <SortableHeader column="status" label="Status" {...sortProps} />
          <SortableHeader column="last_updated" label="Last Updated" {...sortProps} />
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {processedRecordings.map(recording => (
          <RecordingRow key={recording.name} recording={recording} />
        ))}
      </tbody>
    </table>
  </div>
);
```

### FilterPanel Design

```typescript
// FilterPanel.tsx
<div style={{ 
  marginBottom: '20px',
  padding: isVisible ? '20px' : '0',
  height: isVisible ? 'auto' : '0',
  overflow: 'hidden',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  backgroundColor: '#f9fafb',
  transition: 'all 0.3s ease'
}}>
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
    
    {/* Search Box */}
    <div>
      <label>Search</label>
      <input 
        type="text"
        placeholder="Search recordings..."
        value={filterConfig.searchTerm}
        onChange={(e) => updateFilter('searchTerm', e.target.value)}
      />
    </div>

    {/* Status Filter */}
    <div>
      <label>Status</label>
      <select 
        value={filterConfig.status}
        onChange={(e) => updateFilter('status', e.target.value)}
      >
        <option value="all">All Statuses</option>
        <option value="Recorded">📹 Recorded</option>
        <option value="Extracted">📁 Extracted</option>
        <option value="Analyzed">📊 Analyzed</option>
        <option value="SetupRendered">🎬 Setup</option>
        <option value="Rendered">✅ Rendered</option>
        <option value="Uploaded">🚀 Uploaded</option>
        <option value="Failed">❌ Failed</option>
      </select>
    </div>

    {/* Date Range Quick Filters */}
    <div>
      <label>Date Range</label>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <button onClick={() => setDateRange('24h')}>Last 24h</button>
        <button onClick={() => setDateRange('7d')}>Last 7d</button>
        <button onClick={() => setDateRange('30d')}>Last 30d</button>
      </div>
    </div>

    {/* Actions */}
    <div style={{ display: 'flex', alignItems: 'end', gap: '8px' }}>
      <button onClick={onClearFilters}>Clear All</button>
    </div>

  </div>
</div>
```

### SortableHeader Design

```typescript
// SortableHeader.tsx
<th 
  onClick={() => onSort(column)}
  style={{ 
    padding: '12px 8px',
    textAlign: 'left',
    fontWeight: '600',
    borderBottom: '1px solid #e5e7eb',
    cursor: 'pointer',
    userSelect: 'none',
    backgroundColor: sortConfig.column === column ? '#f3f4f6' : 'transparent',
    ':hover': { backgroundColor: '#f3f4f6' }
  }}
>
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <span>{label}</span>
    <span style={{ marginLeft: '8px', opacity: 0.6 }}>
      {sortConfig.column === column ? (
        sortConfig.direction === 'asc' ? '↑' : '↓'
      ) : (
        '↕️'
      )}
    </span>
  </div>
</th>
```

## Etapy Implementacji

### Phase 1: Basic Sorting (2-3h)
**Priorytet: Wysoki**

1. Implementacja `useSortingAndFiltering` hook
2. Komponent `SortableHeader` 
3. Podstawowe sortowanie: name, status, last_updated
4. Wizualne wskaźniki sortowania

**Deliverables:**
- Klikalne nagłówki z ikonami
- Sortowanie po nazwach (alfabetyczne)
- Sortowanie po dacie (chronologiczne) 
- Sortowanie po statusie (priorytet)

### Phase 2: Search & Status Filter (2-3h)
**Priorytet: Wysoki**

1. Search box dla nazw nagrań
2. Status dropdown filter
3. Komponent `FilterPanel` (podstawowy)
4. Integration z sortowaniem

**Deliverables:**
- Real-time search w nazwach
- Filtr po statusie
- Panel filtrów (minimalistyczny)
- Licznik wyników

### Phase 3: Advanced Filters (3-4h)
**Priorytet: Średni**

1. Date range filters (quick + custom)
2. File size filters
3. Zaawansowany UI dla filtrów
4. Persistence filtrów w localStorage

**Deliverables:**
- Date range filtering
- Size range filtering
- Advanced filter panel UI
- Filter persistence

### Phase 4: UX Enhancements (2-3h)
**Priorytet: Niski**

1. Animacje collapse/expand
2. Keyboard shortcuts (Ctrl+F dla search)
3. URL parameters dla shared filters
4. Export filtered results

**Deliverables:**
- Smooth animations
- Keyboard navigation
- Shareable filter URLs
- Export functionality

## Przypadki Użycia

### UC1: Szybkie wyszukanie nagrania
**Kroki:**
1. Użytkownik wpisuje część nazwy w search box
2. Lista filtruje się w real-time
3. Użytkownik klika na wynik

### UC2: Znalezienie failed recordings
**Kroki:**
1. Użytkownik otwiera panel filtrów
2. Wybiera "Failed" w dropdown status
3. Lista pokazuje tylko nieudane nagrania

### UC3: Sortowanie według najnowszych
**Kroki:**
1. Użytkownik klika nagłówek "Last Updated"
2. Lista sortuje się od najnowszych
3. Powtórne kliknięcie odwraca kolejność

### UC4: Znalezienie dużych plików
**Kroki:**
1. Użytkownik otwiera panel filtrów
2. Ustawia filtr "Large files (>5GB)"
3. Lista pokazuje tylko duże nagrania

## Success Criteria

1. **Performance**: Sortowanie i filtrowanie < 100ms dla 1000+ recordings
2. **Usability**: Intuicyjne UI nie wymagające instrukcji
3. **Functionality**: Wszystkie kombinacje filtrów działają poprawnie
4. **Persistence**: Filtry zachowują się po refresh strony
5. **Accessibility**: Keyboard navigation i screen reader support

## Pytania do Rozstrzygnięcia

1. **Default sorting**: Last Updated (desc) czy Recording Name (asc)?
2. **Filter persistence**: localStorage czy URL parameters?
3. **Advanced filters**: Czy potrzebujemy custom date range picker?
4. **Performance**: Czy implementować virtualizację dla 1000+ recordings?
5. **Keyboard shortcuts**: Które shortcuts są najbardziej przydatne?

## Zależności

### Nowe Dependencies
```json
// package.json
{
  "date-fns": "^3.0.0",  // Date manipulation
  "lodash.debounce": "^4.0.8"  // Search debouncing
}
```

### Optional Dependencies (Phase 4)
```json
{
  "react-datepicker": "^4.0.0",  // Advanced date picker
  "file-saver": "^2.0.0"  // Export functionality
}
```

### Performance Considerations
- Debounced search (300ms delay)
- Memoized sorting functions
- Virtual scrolling dla 1000+ items (opcjonalne)
- Lazy loading dla bardzo dużych zbiorów

## Kompatybilność

### Integracja z Istniejącym Kodem
- ✅ Hook pattern pasuje do `useRecordings`
- ✅ Tabela HTML gotowa na rozszerzenie
- ✅ TypeScript types są kompatybilne
- ✅ Styling inline nie konfliktuje

### Backend Compatibility
- ✅ Brak potrzeby zmian w Rust backend
- ✅ Wszystko dzieje się na frontend
- ✅ Istniejące API commands wystarczą 