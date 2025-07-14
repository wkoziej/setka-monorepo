# OBSession

System automatycznej ekstrakcji źródeł z nagrań canvas OBS na podstawie metadanych pozycji zapisanych podczas nagrywania.

Automatyczna ekstrakcja źródeł z nagrania canvas OBS wykorzystująca:
- OBS API do detekcji capabilities źródeł (audio/video)
- Metadane pozycji zapisane podczas nagrywania
- FFmpeg do precyzyjnej ekstrakcji

## 🏗️ Architektura Systemu

### Główne Komponenty

#### 1. **Core Modules** (`src/core/`)
- **`metadata.py`**: Zarządzanie metadanymi i detekcja capabilities
  - `determine_source_capabilities()` - OBS API do detekcji audio/video
  - `create_metadata()` - tworzenie struktury metadanych
  - `validate_metadata()` - walidacja struktury
  
- **`extractor.py`**: Ekstrakcja źródeł przez FFmpeg
  - `extract_sources()` - główna funkcja ekstrakcji
  - `ExtractionResult` - klasa wyników
  - `calculate_crop_params()` - obliczanie parametrów crop
  - `sanitize_filename()` - bezpieczne nazwy plików

#### 2. **OBS Integration** (`src/obs_integration/`)
- **`obs_script.py`**: Główny skrypt OBS Studio
  - Event handlers dla start/stop recording
  - Automatyczne zbieranie metadanych sceny
  - Konfiguracja przez OBS UI
  
- **`scene_analyzer.py`**: Analiza scen OBS
  - `SceneAnalyzer` - klasa do analizy scen
  - Enumeracja źródeł i ich właściwości
  - Backup funkcjonalności dla skryptu

#### 3. **CLI Interface** (`src/cli/`)
- **`extract.py`**: Interface linii komend
  - Argumenty: video_file, metadata_file, --output-dir, --verbose
  - Walidacja plików wejściowych
  - Integracja z core ekstraktorem

### Aktualna Struktura Projektu
```
obsession/
├── src/
│   ├── core/                     # Logika biznesowa
│   │   ├── metadata.py           # Zarządzanie metadanymi + OBS API
│   │   └── extractor.py          # Ekstrakcja źródeł (FFmpeg)
│   │
│   ├── obs_integration/          # Integracja z OBS Studio
│   │   ├── obs_script.py         # Skrypt OBS (Python)
│   │   └── scene_analyzer.py     # Analiza scen OBS
│   │
│   └── cli/                      # Interface linii komend
│       └── extract.py            # CLI dla ekstrakcji
│
├── tests/                        # Testy (78 testów, 100% pass)
│   ├── test_metadata.py          # Testy metadanych + capabilities
│   ├── test_extractor.py         # Testy ekstraktora
│   ├── test_obs_script.py        # Testy integracji OBS
│   ├── test_scene_analyzer.py    # Testy analizy scen
│   ├── test_cli.py               # Testy CLI
│   └── conftest.py               # Konfiguracja testów
│
├── pyproject.toml                # Konfiguracja projektu (uv)
├── pytest.ini                   # Konfiguracja testów
└── uv.lock                       # Lock file dependencies
```

## 🚀 Workflow Systemu

```mermaid
graph LR
    A[Układam źródła w OBS] --> B[Start Recording]
    B --> C[OBS Script zbiera metadane]
    C --> D[Stop Recording]
    D --> E[Automatyczna ekstrakcja]
    E --> F[Osobne pliki video/audio]
```

### 1. Przygotowanie w OBS
- Ułóż źródła na canvas (mozaika)
- Załaduj `obs_script.py` w OBS Studio
- Konfiguruj ścieżkę zapisu metadanych

### 2. Nagrywanie
- Start Recording → skrypt przygotowuje metadane
- Stop Recording → skrypt zapisuje pełne metadane z capabilities

### 3. Ekstrakcja
```bash
# Automatycznie lub ręcznie
uv run python -m cli.extract recording.mkv metadata.json
```

## 📊 Format Metadanych (v2.0)

### Nowy format z capabilities:
```json
{
  "canvas_size": [1920, 1080],
  "fps": 30.0,
  "recording_start_time": 1751709738.0,
  "scene_name": "Scena",
  "sources": {
    "Camera1": {
      "name": "Camera1",
      "id": "v4l2_input",
      "position": {"x": 0, "y": 0},
      "scale": {"x": 1.0, "y": 1.0},
      "dimensions": {
        "source_width": 1920,
        "source_height": 1080,
        "final_width": 1920,
        "final_height": 1080
      },
      "visible": true,
      "has_audio": true,    // ← Nowe pole (OBS API)
      "has_video": true     // ← Nowe pole (OBS API)
    },
    "Microphone": {
      "name": "Microphone",
      "id": "pulse_input_capture",
      "position": {"x": 0, "y": 0},
      "has_audio": true,
      "has_video": false
    }
  },
  "recording_stop_time": 1751709739.5,
  "total_sources": 2
}
```

## 🔧 Instalacja i Setup

### Wymagania
- **Python 3.9+**
- **FFmpeg 4.4+** (w PATH)
- **OBS Studio 28+**
- **uv** (package manager)

### Instalacja
```bash
# 1. Klonuj repozytorium
git clone https://github.com/wkoziej/obsession.git
cd obsession

# 2. Zainstaluj dependencies
uv sync

# 3. Uruchom testy (sprawdź czy wszystko działa)
uv run pytest

# 4. Załaduj skrypt w OBS Studio
# OBS → Tools → Scripts → Add → src/obs_integration/obs_script.py
```

### Konfiguracja OBS Script
1. W OBS: Tools → Scripts → Add
2. Wybierz `src/obs_integration/obs_script.py`
3. Ustaw ścieżkę zapisu metadanych
4. Włącz "Enable metadata collection"

## 🎮 Użycie

### CLI Interface
```bash
# Podstawowa ekstrakcja
uv run python -m cli.extract recording.mkv metadata.json

# Z verbose output
uv run python -m cli.extract recording.mkv metadata.json --verbose

# Pomoc
uv run python -m cli.extract --help
```

### Programmatic API
```python
from src.core.extractor import extract_sources
import json

# Wczytaj metadane
with open("metadata.json", "r") as f:
    metadata = json.load(f)

# Ekstraktuj źródła
result = extract_sources("recording.mkv", metadata)

if result.success:
    print(f"Extracted {len(result.extracted_files)} files:")
    for file in result.extracted_files:
        print(f"  - {file}")
else:
    print(f"Error: {result.error_message}")
```

## 📁 Wyniki Ekstrakcji

### Struktura wyjściowa:
```
recording_20250105_143022_extracted/
├── Camera1.mp4              # Video z Camera1
├── Camera1.m4a              # Audio z Camera1  
├── Microphone.m4a           # Audio z Microphone (tylko audio)
├── ScreenCapture.mp4        # Video z ScreenCapture (tylko video)
└── ...
```

### Logika ekstrakcji:
- **`has_video=true`** → plik `.mp4` (crop filter, bez audio `-an`)
- **`has_audio=true`** → plik `.m4a` (bez video `-vn`)
- **`has_audio=false && has_video=false`** → pomijane
- **Bezpieczne nazwy plików**: znaki specjalne zastąpione `_`

## ⚙️ Techniczne Szczegóły

### Detekcja Capabilities
System używa OBS API do precyzyjnej detekcji możliwości źródeł:
```python
flags = obs.obs_source_get_output_flags(obs_source)
OBS_SOURCE_VIDEO = 0x001  # Źródło ma video
OBS_SOURCE_AUDIO = 0x002  # Źródło ma audio
```

### Parametry FFmpeg
- **Video**: H.264, CRF 23, preset fast, crop filter
- **Audio**: AAC, 128kbps, bez video (`-vn`)
- **Crop**: `crop=width:height:x:y` na podstawie pozycji w OBS


## 🧪 System Testowy (TDD)

### Status testów: ✅ 78/78 (100%)

```bash
# Uruchom wszystkie testy
uv run pytest

# Testy z coverage
uv run pytest --cov=src --cov-report=html

# Tylko testy jednostkowe
uv run pytest tests/test_metadata.py tests/test_extractor.py

# Testy integracji OBS
uv run pytest tests/test_obs_script.py tests/test_scene_analyzer.py
```

### Główne kategorie testów:
- **Metadata**: Tworzenie, walidacja, capabilities detection
- **Extractor**: Ekstrakcja video/audio, crop parameters, error handling  
- **OBS Integration**: Script functionality, scene analysis
- **CLI**: Argument parsing, file handling, error reporting

### Standardy:
- **TDD**: Red → Green → Refactor
- **Test coverage**: 78% (cel: >90%)
- **Code style**: Ruff formatting
- **Commits**: Atomic z testami
