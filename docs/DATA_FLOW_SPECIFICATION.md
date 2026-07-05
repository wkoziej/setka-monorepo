# Specyfikacja Przepływu Danych - Setka Monorepo

> Źródłem prawdy dla formatu `analysis.json` jest kod producenta
> `packages/beatrix/src/beatrix/core/audio_analyzer.py`; sekcje poniżej odzwierciedlają
> **faktycznie emitowane** klucze (`schema_version`, `hop_length`, `n_fft`,
> `animation_events.*`, płaskie `frequency_bands.*`). Jedynym konsumentem `analysis.json`
> jest `cymatic` (`packages/cymatic/src/cymatic/analysis_loader.py`), który waliduje
> `schema_version` (brak pola ⇒ przyjmij `1.0`; niezgodny major ⇒ błąd).

## 1. Przegląd Przepływu Danych

```
OBS Recording → obsession → beatrix → cymatic → medusa
```

## 2. Formaty Danych i Interfejsy

### obsession (OBS Recording + Extraction)

**Produkuje:**
```
recording_name/
├── recording_name.mkv          # Plik źródłowy OBS (H.264/AAC)
├── metadata.json              # Metadane sceny OBS
└── extracted/                 # Wyekstrahowane źródła
    ├── Camera1.mp4           # Video (H.264, bez audio)
    ├── Camera2.mp4           # Video (H.264, bez audio)
    ├── Microphone.m4a        # Audio (AAC, bez video)
    └── Desktop_Audio.m4a     # Audio (AAC, bez video)
```

**Format metadata.json** (faktycznie emitowane klucze — patrz `obs_script.py`; brak pola
`version` w produkcji, `canvas_size` to lista, `sources` to słownik):
```json
{
  "canvas_size": [1920, 1080],
  "fps": 30.0,
  "recording_start_time": 1642425422.123456,
  "scene_name": "Main Scene",
  "recording_stop_time": 1642425722.654321,
  "total_sources": 4,
  "sources": {
    "Camera1": {
      "name": "Camera1",
      "id": "v4l2_input",
      "position": {"x": 0, "y": 0},
      "scale": {"x": 1.0, "y": 1.0},
      "bounds": {"x": 960.0, "y": 540.0, "type": 0},
      "dimensions": {
        "source_width": 1920,
        "source_height": 1080,
        "final_width": 960,
        "final_height": 540
      },
      "visible": true,
      "has_audio": false,
      "has_video": true
    },
    "Microphone": {
      "name": "Microphone",
      "id": "pulse_input_capture",
      "position": {"x": 0, "y": 0},
      "scale": {"x": 1.0, "y": 1.0},
      "bounds": {"x": 0.0, "y": 0.0, "type": 0},
      "dimensions": {
        "source_width": 0,
        "source_height": 0,
        "final_width": 0,
        "final_height": 0
      },
      "visible": true,
      "has_audio": true,
      "has_video": false
    }
  }
}
```

---

### beatrix (Analiza Audio) - NOWY PAKIET

**Przyjmuje:**
- Pliki audio: `.m4a`, `.mp3`, `.wav`, `.flac`
- Ścieżka do pliku audio z katalogu `extracted/`

**Produkuje** (per ścieżkę; `beatrix analyze-recording` analizuje master + stemy i pisze
manifest `analysis/index.json` — patrz root `AGENTS.md`):
```
recording_name/
└── analysis/
    ├── master_analysis.json     # Analiza miksu master
    ├── <stem>_analysis.json     # Analiza per-stem (opcjonalnie)
    └── index.json               # Manifest discovery (load_analysis_index)
```

**Format analysis.json** (źródło prawdy: `audio_analyzer.py`, `AudioAnalyzer.analyze_for_animation`):
```json
{
  "schema_version": "1.0",
  "hop_length": 512,
  "n_fft": 2048,
  "duration": 300.45,
  "sample_rate": 44100,
  "tempo": {
    "bpm": 120.18,
    "beat_times": [0.51, 1.01, 1.51, 2.01, 2.51],
    "beat_count": 599
  },
  "animation_events": {
    "beats": [0.51, 4.51, 8.51],
    "sections": [
      {"start": 0.0, "end": 32.1, "label": "section_1"},
      {"start": 32.1, "end": 96.4, "label": "section_2"}
    ],
    "onsets": [0.12, 2.54, 5.02],
    "energy_peaks": [0.50, 2.50, 4.50]
  },
  "frequency_bands": {
    "times": [0.0, 0.012, 0.023],
    "bass_energy": [0.182, 0.091, 0.067],
    "mid_energy": [0.087, 0.077, 0.049],
    "high_energy": [0.045, 0.023, 0.002]
  }
}
```

Uwagi do kontraktu (egzekwowane w kodzie producenta):
- `schema_version` jest **autorytatywną** nazwą pola wersji (nie `version`); brak pola u
  konsumenta ⇒ `1.0`, niezgodny major ⇒ twardy błąd.
- `hop_length` (512) rządzi odstępem czasowym `dt` między próbkami `frequency_bands.*`;
  `n_fft` (2048) to realny default `librosa.stft`. `dt = times[1] - times[0]`.
- `animation_events.beats`, `onsets`, `energy_peaks` to płaskie listy timestampów (sekundy);
  `sections` to obiekty `{start, end, label}` (`label` = `section_N`).
- `frequency_bands.*` to **płaskie** równoległe listy (`times`, `bass_energy`, `mid_energy`,
  `high_energy`) — nie zagnieżdżone `range_hz/energy`.
- Wszystkie wartości liczbowe są natywnymi `float`, sanityzowane z NaN/inf przed serializacją.
- Wejście degenerujące (puste / krótkie / cisza) zwraca puste listy zdarzeń bez crasha.

**Biblioteki używane:**
- `librosa` - analiza tempo, beat tracking, spectral analysis
- `numpy` - przetwarzanie danych
- `scipy` - peak detection, signal processing

---

### cymatic (Blender Geometry Nodes 3D Visualizer)

**Przyjmuje:**
```
recording_name/
└── analysis/                  # Z beatrix - analiza audio
    └── *_analysis.json       # JSON z danymi analizy (schema_version 1.0)
```
(opcjonalnie plik audio do podłożenia pod render; bez niego render jest cichy)

**Produkuje:**
```
recording_name/
└── blender/
    └── render/
        └── <name>.mp4        # Wyrenderowane video (klatki PNG zmuxowane ffmpegiem)
```

**Wykonanie (headless):** `cymatic-render` ładuje `analysis.json` (host-side,
`analysis_loader.load_analysis`), serializuje `VisualizerConfig` do pliku JSON i wywołuje
Blendera bez GUI:
```bash
blender --background --python blender_script/build_scene.py -- --config <config.json>
```
Blender renderuje klatki PNG (ten build 5.1.2 nie ma wbudowanego enkodera wideo), a `runner.py`
muxuje je `ffmpeg`iem do mp4 (post-fx: bloom/vignette/grade w `-filter_complex`, nie w
kompozytorze Blendera). `dt` (odstęp czasowy próbek audio) pochodzi z `analysis.json`
(`times[1] - times[0]`) i musi dotrzeć do każdego węzła `DIVIDE` w grafach Geometry Nodes.

Konfiguracja jest przekazywana **plikiem JSON** (`--config`), nie zmiennymi środowiskowymi.
`VisualizerConfig` niesie m.in.: `output_mp4`, `base_directory`, `fps` (z configu, NIE z analizy;
domyślnie 30), `resolution` (`(w, h)` lub `None`), parametry presetu (`PresetParams`). cymatic
**nie** zapisuje `render_metadata.json`.

---

### medusa (Media Upload & Publishing)

**Przyjmuje:**
```
recording_name/
└── blender/
    └── render/
        └── <name>.mp4  # Video do uploadu (z cymatic)
```

**Dodatkowo przyjmuje upload_config.json:**
```json
{
  "version": "1.0",
  "media": {
    "title": "My Recording",
    "description": "Description of the recording",
    "tags": ["tag1", "tag2", "tag3"],
    "category": "Entertainment",
    "privacy": "public"
  },
  "platforms": {
    "youtube": {
      "enabled": true,
      "playlist_id": "PLxxxxxx",
      "thumbnail": "path/to/thumbnail.jpg",
      "scheduled_time": null
    },
    "facebook": {
      "enabled": true,
      "page_id": "123456789",
      "access_token": "your_facebook_access_token",
      "app_id": "your-app-id",
      "app_secret": "your-app-secret",
      "api_version": "v19.0",
      "message": "Check out my new video!",
      "scheduled_time": "2024-01-15T15:00:00Z"
    },
    "vimeo": {
      "enabled": false
    }
  }
}
```

**Produkuje:**
```
recording_name/
└── uploads/
    ├── upload_results.json    # Rezultaty uploadu
    └── social_posts.json      # Linki do postów
```

**Format upload_results.json:**
```json
{
  "version": "1.0",
  "upload_time": 1642427000.123,
  "results": {
    "youtube": {
      "status": "success",
      "video_id": "dQw4w9WgXcQ",
      "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "upload_time": 1642427100.456,
      "processing_status": "completed"
    },
    "facebook": {
      "status": "success",
      "post_id": "123456789_987654321",
      "url": "https://facebook.com/page/videos/987654321",
      "scheduled": true,
      "publish_time": "2024-01-15T15:00:00Z"
    }
  }
}
```

---

## 3. Pakiety i Ich Odpowiedzialności

### setka-common
**Dostarcza:**
- `RecordingStructureManager` - zarządzanie strukturą katalogów
- `FileExtensions` - stałe dla rozszerzeń plików
- `MediaType` - enum dla typów mediów
- Wspólne narzędzia do walidacji ścieżek

### obsession
**Odpowiada za:**
- Integracja z OBS Studio (obs_script.py)
- Ekstrakcja źródeł z nagrań OBS przy użyciu FFmpeg
- Tworzenie i zarządzanie metadata.json
- Określanie capabilities źródeł (has_audio, has_video)

### beatrix (NOWY)
**Odpowiada za:**
- Analiza plików audio (tempo, beat detection)
- Analiza energii i peak detection
- Analiza spektralna (frequency bands)
- Segmentacja strukturalna audio
- Generowanie JSON z danymi analizy

### cymatic
**Odpowiada za:**
- Budowę sceny Blender Geometry Nodes sterowanej analizą audio (mostek audio→mesh, sampler GN)
- Headless render klatek PNG i mux do mp4 (ffmpeg) pod `blender/render/`
- Walidację kontraktu `analysis.json` (`schema_version`) i per-track `dt`
- Brief struktury audio dla autorskiego cięcia klipów (`cymatic-structure-brief`)

### medusa
**Odpowiada za:**
- Upload video na platformy hostingowe (YouTube, Vimeo)
- Publikacja na social media (Facebook, Twitter)
- Zarządzanie harmonogramem publikacji
- Raportowanie rezultatów

## 4. Przepływ Danych - Przykład

```bash
# 1. Nagranie w OBS generuje
recording_20240115_120000/
├── recording_20240115_120000.mkv
└── metadata.json

# 2. obsession ekstrahuje źródła
obs-extract recording_20240115_120000.mkv --auto
# Tworzy:
recording_20240115_120000/
└── extracted/
    ├── Camera1.mp4
    ├── Camera2.mp4
    └── Microphone.m4a

# 3. beatrix analizuje audio
beatrix analyze recording_20240115_120000/extracted/Microphone.m4a recording_20240115_120000/analysis
# Tworzy:
recording_20240115_120000/
└── analysis/
    └── Microphone_analysis.json

# 4. cymatic renderuje wizualizer 3D
cymatic-render recording_20240115_120000 --main-audio Microphone.m4a
# Tworzy:
recording_20240115_120000/
└── blender/
    └── render/
        └── recording_20240115_120000.mp4

# 5. medusa uploaduje video
medusa upload recording_20240115_120000/blender/render/recording_20240115_120000.mp4 --config upload_config.json
# Tworzy:
recording_20240115_120000/
└── uploads/
    └── upload_results.json
```

## 5. Walidacja Danych

Każdy pakiet powinien walidować swoje wejście:

- **obsession**: Sprawdza czy plik .mkv istnieje i jest czytelny
- **beatrix**: Waliduje format audio, sprawdza minimalną długość
- **cymatic**: Weryfikuje obecność `analysis.json` i waliduje jego `schema_version`
- **medusa**: Sprawdza rozmiar pliku, format video, obecność konfiguracji

## 6. Wersjonowanie Formatów

Formaty JSON niosą pole wersji pozwalające na migrację, kompatybilność wsteczną i jasną
komunikację zmian:
- **`analysis.json`** (beatrix → cymatic): pole **`schema_version`** (autorytatywne).
  Brak pola u konsumenta ⇒ przyjmij `1.0`; niezgodny **major** ⇒ twardy błąd.
- **`upload_config.json` / `upload_results.json`** (medusa): pole `version`.
