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

export interface OperationState {
  running: boolean;
  output: string;
  error: string | null;
}

// Deletion types
export interface DeletionConfirmationState {
  isOpen: boolean;
  recording?: Recording;
  isDeleting: boolean;
}

// Rename types
export interface RenameConfirmationState {
  isOpen: boolean;
  recording?: Recording;
  isRenaming: boolean;
} 