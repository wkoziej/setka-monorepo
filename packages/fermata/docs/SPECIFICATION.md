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
- Status każdego etapu: extracted → analyzed → config_generated → setup_rendered → rendered → uploaded
- Metadane z każdego etapu (rozmiar plików, czas przetwarzania, selected animation preset)
- Podgląd błędów jeśli wystąpiły
- Edycja YAML konfiguracji przed setup

### 2. Zarządzanie Workflow

**F2.1 Uruchamianie Etapów**
- Przycisk "Run Next Step" dla nagrania
- Możliwość uruchomienia konkretnego etapu (beatrix analyze, cinemon config generation, cinemon setup, medusa upload)
- Animation preset selection dla cinemon etapu
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
- Animation preset selection (vintage, modern, minimal, etc.)
- YAML config template generation and editing

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
├── *.mkv                    → recorded (obsession done)
├── extracted/               → extracted
├── analysis/                → analyzed (beatrix done)
├── animation_config_*.yaml  → config_generated (cinemon config ready)
├── blender/                 → setup_rendered (cinemon created .blend project)
│   ├── *.blend
│   └── render/
│       └── *.mp4            → rendered (blender rendering complete)
└── uploads/                 → uploaded (medusa done)
```

**Uruchamianie Etapów:**
```bash
# Beatrix analyze
uv run --package beatrix analyze recording_dir/extracted/audio.m4a

# Cinemon config generation with presets
cinemon-generate-config recording_dir --preset vintage

# Cinemon setup (creates .blend project using YAML config)
cinemon-blend-setup recording_dir --config recording_dir/animation_config_vintage.yaml

# Manual Blender render (user runs this manually or via script)
blender -b recording_dir/blender/project.blend -o recording_dir/blender/render/frame_#### -f 1

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
│ stream_20240115_180000│ 🎬 Setup    │ 10 min ago   │ [Render]│
└─────────────────────────────────────────────────────────────┘
```

### Szczegóły Nagrania
```
┌─────────────────────────────────────────────────────────────┐
│ stream_20240115_120000                              [< Back] │
├─────────────────────────────────────────────────────────────┤
│ Pipeline Status:                                            │
│ ✅ Recorded → ✅ Extracted → ✅ Analyzed → ✅ Config → 🎬 Setup → ⏳ Render → Upload │
├─────────────────────────────────────────────────────────────┤
│ Files:                                                      │
│ 📹 recording.mkv (2.3GB)    📁 extracted/ (5 files)        │
│ 📊 analysis/ (1 file)       ⚙️ animation_config_vintage.yaml │
│ 🎬 blender/ (.blend project)                               │
├─────────────────────────────────────────────────────────────┤
│ Actions: [Generate Config] [Edit Config] [Render in Blender] [Re-setup] [View Logs] │
├─────────────────────────────────────────────────────────────┤
│ Recent Logs:                                                │
│ [14:30] cinemon: Blender project created successfully       │
│ [14:28] cinemon: Applied vintage animation preset          │
│ [14:25] cinemon: Processing compositional animations...     │
│ [14:22] cinemon: Generated YAML config with vintage preset │
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

## YAML Configuration System

### Animation Presets
Fermata now supports animation preset selection with the cinemon config generator:

**Available Presets:**
- `vintage`: Film grain, sepia toning, vintage color grading, rotation wobbles
- `modern`: Clean scale animations with bass response
- `minimal`: Subtle effects with reduced intensity
- `custom`: User-defined template for manual editing

**Workflow Integration:**
1. User selects animation preset in GUI
2. `cinemon-generate-config recording_dir --preset vintage` generates YAML config
3. User can optionally edit YAML config in GUI text editor
4. `cinemon-blend-setup recording_dir --config animation_config_vintage.yaml` creates Blender project
5. YAML→JSON fallback ensures compatibility with Blender environment

### Technical Implementation
- **Config Generation**: CinemonConfigGenerator creates YAML configs from presets and auto-discovered media
- **Blender Integration**: YAML configs converted to JSON before passing to Blender (no PyYAML dependency)
- **Status Detection**: New `config_generated` status detected by presence of `animation_config_*.yaml` files
- **UI Integration**: PresetSelector component in React frontend for preset selection

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
