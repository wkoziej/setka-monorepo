// Recording types matching Rust structs
export interface Recording {
  name: string;
  path: string;
  status: RecordingStatus;
  last_updated: number;
  file_sizes: Record<string, number>;
}

export type RecordingStatus =
  | 'Recorded'
  | 'Extracted'
  | 'Analyzed'
  | 'SetupRendered'
  | 'Rendered'
  | 'Uploaded'
  | { Failed: string };

// Configuration types
export interface AppConfig {
  recordings_path: string;
  cli_paths: CliPaths;
}

export interface CliPaths {
  uv_path: string;
  workspace_root: string;
}

// Operation types
export interface ProcessResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number | null;
}

export type NextStep =
  | 'Extract'
  | 'Analyze'
  | 'Render'
  | 'Upload';

// UI State types
export interface RecordingListState {
  recordings: Recording[];
  loading: boolean;
  error: string | null;
}

export interface DeletionState {
  isOpen: boolean;
  recording: Recording | null;
  isDeleting: boolean;
}

export interface RenameState {
  isOpen: boolean;
  recording: Recording | null;
  isRenaming: boolean;
}

export interface OperationState {
  running: Record<string, boolean>;
  output: string | null;
  error: string | null;
}

// Video types
export interface VideoFile {
  name: string;
  path: string;
  size: number;
  format: string;
  duration?: number;
  thumbnail?: string;
}

export interface VideoInfo {
  duration: number;
  width: number;
  height: number;
  codec: string;
  bitrate: number;
  fps: number;
}

// Preset types
export interface PresetConfig {
  name: string;
  description: string;
  settings: Record<string, any>;
}

export interface PresetOption {
  name: string;
  description: string;
}

export const AVAILABLE_PRESETS: PresetOption[] = [
  {
    name: 'beat-switch',
    description: 'Dynamic camera switching synchronized with beat detection'
  },
  {
    name: 'minimal',
    description: 'Clean, simple layout with minimal animations'
  },
  {
    name: 'music-video',
    description: 'High-energy effects perfect for music content'
  },
  {
    name: 'vintage',
    description: 'Retro-style effects with film grain and color grading'
  }
];

// Sorting and Filtering types
export type SortOption =
  | 'date-desc'    // Newest First (default)
  | 'date-asc'     // Oldest First
  | 'status'       // By Status
  | 'name-asc'     // Name A→Z
  | 'name-desc'    // Name Z→A
  | 'size-desc'    // Largest First
  | 'size-asc';    // Smallest First

export interface FilterConfig {
  searchTerm: string;
  status: RecordingStatus | 'all';
  sortOption: SortOption;
}

export const DEFAULT_FILTERS: FilterConfig = {
  searchTerm: '',
  status: 'all',
  sortOption: 'date-desc'
};

// Controls Bar component props
export interface ControlsBarProps {
  filterConfig: FilterConfig;
  onUpdateFilter: (key: keyof FilterConfig, value: any) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

// Results Counter component props
export interface ResultsCounterProps {
  filteredCount: number;
  totalCount: number;
  hasActiveFilters: boolean;
}
