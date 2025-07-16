# fermata - GUI do Zarządzania Nagraniami

## Cel

Desktop aplikacja (Tauri) do zarządzania i przeglądania nagrań oraz ich statusu w przepływie przetwarzania setka-monorepo:
`OBS Recording → obsession → beatrix → cinemon → medusa`

## Wymagania Funkcjonalne

### 1. Przeglądanie Nagrań

**F1.1 Lista Nagrań**
- Wyświetlanie wszystkich nagrań z skonfigurowanego katalogu
- Kolumny: Nazwa, Data nagrania, Aktualny status, Ostatnia aktywność
- Sortowanie i filtrowanie po statusie/dacie
- Auto-refresh przy wykryciu nowych nagrań (file watching)

**F1.2 Szczegóły Nagrania**
- Widok szczegółowy pojedynczego nagrania
- Status każdego etapu: extracted → analyzed → rendered → uploaded
- Metadane z każdego etapu (rozmiar plików, czas przetwarzania)
- Podgląd błędów jeśli wystąpiły

### 2. Zarządzanie Workflow

**F2.1 Uruchamianie Etapów**
- Przycisk "Run Next Step" dla nagrania
- Możliwość uruchomienia konkretnego etapu (beatrix analyze, cinemon render, medusa upload)
- Batch operations - uruchomienie operacji na wielu nagraniach

**F2.2 Monitoring Operacji**
- Real-time output z uruchomionych CLI commands
- Status: pending/running/completed/failed
- Logi błędów i ostrzeżeń

### 3. Konfiguracja

**F3.1 Ustawienia Aplikacji**
- Ścieżka do katalogu z nagraniami
- Konfiguracja CLI paths (beatrix, cinemon, medusa)
- Ustawienia file watching

**F3.2 Workflow Configuration**
- Default parametry dla każdego etapu

## Wymagania Techniczne

### Architektura

**Frontend**: React + TypeScript
- Komponenty: RecordingList, RecordingDetails, OperationLogs, Settings
- State management: React Context/Zustand
- UI Library: Tailwind CSS + shadcn/ui

**Backend**: Rust (Tauri)
- File system operations
- Process spawning (CLI commands)
- File watching
- Configuration management

**Komunikacja**: 
- Tauri invoke/emit dla frontend ↔ backend
- Subprocess dla Rust → Python CLI commands

### Integracja z Istniejącymi Pakietami

**Wykrywanie Statusu Nagrania:**
```rust
// Sprawdzanie obecności plików/katalogów:
recording_dir/
├── *.mkv           → recorded (obsession done)
├── extracted/      → extracted  
├── analysis/       → analyzed (beatrix done)
├── blender/render/ → rendered (cinemon done)
└── uploads/        → uploaded (medusa done)
```

**Uruchamianie Etapów:**
```bash
# Beatrix analyze
uv run --package beatrix analyze recording_dir/extracted/audio.m4a

# Cinemon render  
uv run --package cinemon cinemon-blend-setup recording_dir --animation-mode beat-switch

# Medusa upload
uv run --package medusa upload recording_dir/blender/render/final.mp4 --config config.json
```

## Wymagania UX

### Główne Okno
```
┌─────────────────────────────────────────────────────────────┐
│ fermata - Recording Manager                           [⚙️ Settings] │
├─────────────────────────────────────────────────────────────┤
│ Recording Name        │ Status      │ Last Updated │ Actions │
├─────────────────────────────────────────────────────────────┤
│ stream_20240115_120000│ ✅ Rendered │ 2 hours ago  │ [Upload]│
│ stream_20240115_140000│ 🔄 Analyzing│ 30 min ago   │ [View]  │
│ stream_20240115_160000│ ❌ Failed   │ 1 hour ago   │ [Retry] │
│ stream_20240115_180000│ 📁 Extracted│ 10 min ago   │ [Analyze]│
└─────────────────────────────────────────────────────────────┘
```

### Szczegóły Nagrania
```
┌─────────────────────────────────────────────────────────────┐
│ stream_20240115_120000                              [< Back] │
├─────────────────────────────────────────────────────────────┤
│ Pipeline Status:                                            │
│ ✅ Recorded    → ✅ Extracted → ✅ Analyzed → ✅ Rendered → ⏳ Upload │
├─────────────────────────────────────────────────────────────┤
│ Files:                                                      │
│ 📹 recording.mkv (2.3GB)    📁 extracted/ (5 files)        │
│ 📊 analysis/ (1 file)       🎬 blender/render/ (1 file)     │
├─────────────────────────────────────────────────────────────┤
│ Actions: [Upload to YouTube] [Re-render] [View Logs]        │
├─────────────────────────────────────────────────────────────┤
│ Recent Logs:                                                │
│ [14:30] cinemon: Rendering completed successfully           │
│ [14:25] cinemon: Processing beat-switch animations...       │
│ [14:20] cinemon: Loading audio analysis data               │
└─────────────────────────────────────────────────────────────┘
```

## Phases of Development

### Phase 1: MVP
- Podstawowe wykrywanie statusu nagrań
- Lista nagrań z podstawowymi informacjami
- Uruchamianie pojedynczych operacji
- Podstawowa konfiguracja

### Phase 2: Enhanced UX
- Real-time logi z operacji
- Batch operations
- File watching dla auto-refresh
- Ulepszone UI/UX

### Phase 3: Advanced Features
- Profile przetwarzania
- Harmonogram operacji
- Integracja z system notifications
- Export/import konfiguracji

## Structure

```
packages/fermata/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands/          # Tauri commands
│   │   ├── file_watcher.rs    # File system monitoring
│   │   ├── process_runner.rs  # CLI command execution
│   │   └── state.rs          # App state management
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/                      # React frontend
│   ├── components/
│   │   ├── RecordingList.tsx
│   │   ├── RecordingDetails.tsx
│   │   ├── OperationLogs.tsx
│   │   └── Settings.tsx
│   ├── hooks/               # React hooks for Tauri
│   ├── types/              # TypeScript definitions
│   └── App.tsx
├── package.json
├── pyproject.toml          # Python deps (jeśli potrzebne)
└── README.md
```

## Success Criteria

1. **Functionality**: Użytkownik może przeglądać nagrania i uruchamiać wszystkie etapy pipeline
2. **Performance**: Aplikacja responsywnie obsługuje 100+ nagrań
3. **Reliability**: Stabilne uruchamianie CLI commands z właściwym error handling
4. **Usability**: Intuicyjny interface nie wymagający dokumentacji 