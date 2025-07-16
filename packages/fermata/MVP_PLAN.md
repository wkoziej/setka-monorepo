# Plan Realizacji MVP - fermata

## Przegląd MVP

Minimalna wersja aplikacji fermata obejmuje:
1. Wykrywanie statusu nagrań z file systemu
2. Lista nagrań z podstawowymi informacjami  
3. Szczegóły pojedynczego nagrania
4. Uruchamianie następnego etapu pipeline
5. Podstawowa konfiguracja

## Podejście TDD

Każdy komponent będzie realizowany w cyklu:
1. **Red** - Napisanie failing testu
2. **Green** - Minimalna implementacja żeby test przeszedł
3. **Refactor** - Cleanup kodu przy zachowaniu testów

## Struktura MVP

```
packages/fermata/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── lib.rs
│   │   ├── models/
│   │   │   ├── mod.rs
│   │   │   └── recording.rs        # Recording struct + status detection
│   │   ├── commands/
│   │   │   ├── mod.rs
│   │   │   ├── recordings.rs       # Tauri commands for recordings
│   │   │   └── operations.rs       # CLI execution commands
│   │   ├── services/
│   │   │   ├── mod.rs
│   │   │   ├── file_scanner.rs     # Directory scanning
│   │   │   ├── status_detector.rs  # Status detection logic
│   │   │   └── process_runner.rs   # CLI command execution
│   │   └── config.rs              # Configuration management
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/                          # React frontend
│   ├── components/
│   │   ├── RecordingList.tsx
│   │   ├── RecordingDetails.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   └── useRecordings.ts       # React hooks for Tauri
│   ├── types/
│   │   └── index.ts              # TypeScript definitions
│   ├── App.tsx
│   └── main.tsx
├── tests/                        # Integration tests
├── package.json
└── README.md
```

## Fazy Realizacji

### Faza 1: Backend Core (Rust)

#### 1.1 Models & Types
**Test Cases:**
- Test `Recording` struct creation z file path
- Test `RecordingStatus` enum serialization
- Test status detection dla każdego etapu pipeline

**Implementation:**
```rust
// models/recording.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recording {
    pub name: String,
    pub path: PathBuf,
    pub status: RecordingStatus,
    pub last_updated: SystemTime,
    pub file_sizes: HashMap<String, u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RecordingStatus {
    Recorded,    // .mkv exists
    Extracted,   // extracted/ exists
    Analyzed,    // analysis/ exists  
    Rendered,    // blender/render/ exists
    Uploaded,    // uploads/ exists
    Failed(String),
}
```

#### 1.2 Status Detection Service
**Test Cases:**
- Test wykrywania statusu dla każdego etapu
- Test handling missing directories
- Test error cases (permission denied, etc.)

**Implementation:**
```rust
// services/status_detector.rs
impl StatusDetector {
    pub fn detect_status(recording_path: &Path) -> RecordingStatus;
    pub fn get_file_info(recording_path: &Path) -> FileInfo;
    pub fn validate_recording_structure(path: &Path) -> Result<(), String>;
}
```

#### 1.3 File Scanner Service
**Test Cases:**
- Test skanowania katalogu z nagraniami
- Test filtrowania nieprawidłowych katalogów
- Test performance z dużą liczbą nagrań

**Implementation:**
```rust
// services/file_scanner.rs
impl FileScanner {
    pub fn scan_recordings(root_path: &Path) -> Vec<Recording>;
    pub fn is_valid_recording_dir(path: &Path) -> bool;
    pub fn get_recording_name(path: &Path) -> String;
}
```

#### 1.4 Configuration Management
**Test Cases:**
- Test loading/saving konfiguracji
- Test default values
- Test validation ścieżek

**Implementation:**
```rust
// config.rs
#[derive(Debug, Serialize, Deserialize)]
pub struct AppConfig {
    pub recordings_path: PathBuf,
    pub cli_paths: CliPaths,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CliPaths {
    pub uv_path: String,
    pub workspace_root: PathBuf,
}
```

#### 1.5 Tauri Commands
**Test Cases:**
- Test każdego Tauri command z mock data
- Test error handling i serialization
- Integration test z frontend

**Implementation:**
```rust
// commands/recordings.rs
#[tauri::command]
pub fn get_recordings(config: State<AppConfig>) -> Result<Vec<Recording>, String>;

#[tauri::command] 
pub fn get_recording_details(name: String, config: State<AppConfig>) -> Result<Recording, String>;

// commands/operations.rs
#[tauri::command]
pub async fn run_next_step(recording_name: String, config: State<AppConfig>) -> Result<String, String>;

#[tauri::command]
pub async fn run_specific_step(recording_name: String, step: String, config: State<AppConfig>) -> Result<String, String>;
```

### Faza 2: Frontend Core (React + TypeScript)

#### 2.1 Types & Interfaces
**Test Cases:**
- Test TypeScript types zgodności z Rust structs
- Test serialization/deserialization

**Implementation:**
```typescript
// types/index.ts
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
  | 'Rendered' 
  | 'Uploaded' 
  | { Failed: string };

export interface AppConfig {
  recordings_path: string;
  cli_paths: CliPaths;
}
```

#### 2.2 Tauri Hooks
**Test Cases:**
- Test useRecordings hook
- Test error handling
- Test loading states

**Implementation:**
```typescript
// hooks/useRecordings.ts
export function useRecordings() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const refreshRecordings = useCallback(async () => {
    // invoke('get_recordings')
  }, []);
  
  return { recordings, loading, error, refreshRecordings };
}

export function useRecordingOperations() {
  const runNextStep = useCallback(async (recordingName: string) => {
    // invoke('run_next_step', { recordingName })
  }, []);
  
  return { runNextStep };
}
```

#### 2.3 RecordingList Component
**Test Cases:**
- Test renderowania listy nagrań
- Test sortowania i filtrowania
- Test action buttons

**Implementation:**
```tsx
// components/RecordingList.tsx
export function RecordingList() {
  const { recordings, loading, error, refreshRecordings } = useRecordings();
  const { runNextStep } = useRecordingOperations();
  
  // Table z kolumnami: Name, Status, Last Updated, Actions
  // Sortowanie po statusie i dacie
  // Action buttons dla każdego nagrania
}
```

#### 2.4 RecordingDetails Component
**Test Cases:**
- Test wyświetlania szczegółów nagrania
- Test pipeline status visualization
- Test file sizes i metadata

**Implementation:**
```tsx
// components/RecordingDetails.tsx
export function RecordingDetails({ recordingName }: { recordingName: string }) {
  const [recording, setRecording] = useState<Recording | null>(null);
  
  // Pipeline status progress bar
  // File information display
  // Action buttons (specific steps)
}
```

#### 2.5 Settings Component
**Test Cases:**
- Test edycji konfiguracji
- Test walidacji ścieżek
- Test zapisywania ustawień

**Implementation:**
```tsx
// components/Settings.tsx
export function Settings() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  
  // Form dla recordings_path
  // CLI paths configuration
  // Save/Cancel buttons
}
```

### Faza 3: Process Runner & Operations

#### 3.1 Process Runner Service
**Test Cases:**
- Test uruchamiania CLI commands
- Test capturing stdout/stderr
- Test timeout handling
- Test process cancellation

**Implementation:**
```rust
// services/process_runner.rs
pub struct ProcessRunner {
    workspace_root: PathBuf,
    uv_path: String,
}

impl ProcessRunner {
    pub async fn run_beatrix_analyze(&self, recording_path: &Path, audio_file: &str) -> ProcessResult;
    pub async fn run_cinemon_render(&self, recording_path: &Path, animation_mode: &str) -> ProcessResult;
    pub async fn run_medusa_upload(&self, video_path: &Path, config_path: &Path) -> ProcessResult;
}

pub struct ProcessResult {
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: Option<i32>,
}
```

#### 3.2 Next Step Logic
**Test Cases:**
- Test określania następnego kroku dla każdego statusu
- Test edge cases (missing files, etc.)

**Implementation:**
```rust
impl Recording {
    pub fn get_next_step(&self) -> Option<NextStep>;
    pub fn can_run_step(&self, step: &str) -> bool;
    pub fn get_available_steps(&self) -> Vec<String>;
}

pub enum NextStep {
    Extract,  // obs-extract (poza scope MVP)
    Analyze,  // beatrix analyze
    Render,   // cinemon render
    Upload,   // medusa upload
}
```

### Faza 4: Integration & Polish

#### 4.1 Error Handling
- Unified error types w Rust
- Error boundaries w React
- User-friendly error messages

#### 4.2 Loading States
- Progress indicators
- Skeleton loaders
- Operation status feedback

#### 4.3 Configuration Persistence
- Save/load app config
- Default paths detection
- Settings validation

## Testing Strategy

### Unit Tests
- **Rust**: każdy service, model, command
- **TypeScript**: każdy hook, utility function
- **React**: każdy component z React Testing Library

### Integration Tests
- **Tauri Commands**: test full stack calls
- **File System**: test z real directories
- **CLI Integration**: test z mock CLI commands

### End-to-End Tests
- **User Workflows**: complete user journeys
- **Performance**: 100+ recordings handling
- **Error Recovery**: error states i recovery

## Definition of Done

Każda feature jest "done" gdy:

1. ✅ **Unit tests pass** - wszystkie testy jednostkowe przechodzą
2. ✅ **Integration tests pass** - testy integracyjne przechodzą
3. ✅ **Manual testing** - feature działa w aplikacji
4. ✅ **Error handling** - właściwe obsługiwanie błędów
5. ✅ **Documentation** - kod jest udokumentowany
6. ✅ **Performance** - acceptable performance dla target use case

## Kryteria Akceptacji MVP

MVP jest gotowe gdy:

1. ✅ Aplikacja skanuje katalog i wyświetla listę nagrań
2. ✅ Każde nagranie pokazuje właściwy status pipeline
3. ✅ Użytkownik może kliknąć "Next Step" i uruchomić operację
4. ✅ Aplikacja pokazuje szczegóły nagrania z file info
5. ✅ Użytkownik może skonfigurować podstawowe ustawienia
6. ✅ Error handling dla podstawowych błędów
7. ✅ Performance: <2s load time dla 50 nagrań 