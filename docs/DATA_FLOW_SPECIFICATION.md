# Specyfikacja Przepływu Danych - Setka Monorepo

## 1. Przegląd Przepływu Danych

```
OBS Recording → obsession → beatrix → cinemon → medusa
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

**Format metadata.json:**
```json
{
  "version": "2.0",
  "canvas_size": [1920, 1080],
  "fps": 30.0,
  "recording_start_time": 1642425422.123456,
  "recording_stop_time": 1642425722.654321,
  "scene_name": "Main Scene",
  "total_sources": 4,
  "sources": {
    "Camera1": {
      "name": "Camera1",
      "id": "v4l2_input",
      "type": "input",
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
      "type": "input",
      "has_audio": true,
      "has_video": false,
      "audio_settings": {
        "volume": 1.0,
        "muted": false,
        "sync_offset": 0
      }
    }
  }
}
```

---

### beatrix (Analiza Audio) - NOWY PAKIET

**Przyjmuje:**
- Pliki audio: `.m4a`, `.mp3`, `.wav`, `.flac`
- Ścieżka do pliku audio z katalogu `extracted/`

**Produkuje:**
```
recording_name/
└── analysis/
    ├── Microphone_analysis.json     # Analiza głównego audio
    └── Desktop_Audio_analysis.json  # Analiza dodatkowego audio
```

**Format analysis.json:**
```json
{
  "version": "1.0",
  "file_info": {
    "filename": "Microphone.m4a",
    "duration": 300.45,
    "sample_rate": 44100,
    "channels": 2,
    "bit_depth": 16
  },
  "tempo_analysis": {
    "bpm": 120.18,
    "confidence": 0.85,
    "beat_times": [0.51, 1.01, 1.51, 2.01, 2.51],
    "beat_count": 599,
    "time_signature": "4/4"
  },
  "energy_analysis": {
    "rms_mean": 0.045,
    "rms_std": 0.012,
    "energy_peaks": [
      {"time": 0.50, "value": 0.92},
      {"time": 2.50, "value": 0.88},
      {"time": 4.50, "value": 0.95}
    ],
    "silence_regions": [
      {"start": 45.2, "end": 47.8},
      {"start": 125.6, "end": 126.1}
    ]
  },
  "spectral_analysis": {
    "frequency_bands": {
      "times": [0.0, 0.012, 0.023],
      "bass": {
        "range_hz": [20, 250],
        "energy": [0.182, 0.091, 0.067]
      },
      "mid": {
        "range_hz": [250, 4000],
        "energy": [0.087, 0.077, 0.049]
      },
      "high": {
        "range_hz": [4000, 20000],
        "energy": [0.045, 0.023, 0.002]
      }
    }
  },
  "structural_analysis": {
    "sections": [
      {"start": 0.0, "end": 32.1, "label": "intro", "confidence": 0.78},
      {"start": 32.1, "end": 96.4, "label": "verse_1", "confidence": 0.82},
      {"start": 96.4, "end": 128.5, "label": "chorus", "confidence": 0.91}
    ],
    "onset_times": [0.12, 0.54, 1.02, 1.48, 2.01]
  }
}
```

**Biblioteki używane:**
- `librosa` - analiza tempo, beat tracking, spectral analysis
- `numpy` - przetwarzanie danych
- `scipy` - peak detection, signal processing

---

### cinemon (Blender VSE Project)

**Przyjmuje:**
```
recording_name/
├── metadata.json              # Z obsession - info o źródłach
├── extracted/                 # Z obsession - pliki mediów
│   ├── *.mp4                 # Pliki video
│   └── *.m4a                 # Pliki audio
└── analysis/                  # Z beatrix - analiza audio
    └── *_analysis.json       # JSON z danymi analizy
```

**Produkuje:**
```
recording_name/
└── blender/
    ├── recording_name.blend          # Projekt Blender (format binarny)
    ├── vse_script_executed.py        # Zapisany skrypt użyty do generacji
    └── render/
        ├── recording_name_final.mp4  # Wyrenderowane video (H.264/AAC)
        └── render_metadata.json      # Metadane renderowania
```

**Format render_metadata.json:**
```json
{
  "version": "1.0",
  "render_settings": {
    "resolution": [1920, 1080],
    "fps": 30,
    "codec": "h264",
    "audio_codec": "aac",
    "bitrate": "8M",
    "duration": 300.45
  },
  "project_info": {
    "blender_version": "4.3.0",
    "creation_time": 1642426000.123,
    "animation_mode": "beat-switch",
    "video_tracks": ["Camera1.mp4", "Camera2.mp4"],
    "audio_tracks": ["Microphone.m4a"],
    "main_audio": "Microphone.m4a"
  },
  "animation_info": {
    "mode": "beat-switch",
    "keyframe_count": 599,
    "beat_division": 8,
    "effects_applied": ["visibility_switching", "scale_pulsing"]
  }
}
```

**Przekazywanie danych do Blendera (env vars):**
```bash
BLENDER_VSE_RECORDING_DIR="/path/to/recording_name"
BLENDER_VSE_VIDEO_FILES="Camera1.mp4,Camera2.mp4"
BLENDER_VSE_AUDIO_FILES="Microphone.m4a,Desktop_Audio.m4a"
BLENDER_VSE_MAIN_AUDIO="Microphone.m4a"
BLENDER_VSE_OUTPUT_FILE="recording_name.blend"
BLENDER_VSE_FPS="30"
BLENDER_VSE_RESOLUTION="1920x1080"
BLENDER_VSE_ANIMATION_MODE="beat-switch"
BLENDER_VSE_AUDIO_ANALYSIS_FILE="Microphone_analysis.json"
```

---

### medusa (Media Upload & Publishing)

**Przyjmuje:**
```
recording_name/
└── blender/
    └── render/
        ├── recording_name_final.mp4  # Video do uploadu
        └── render_metadata.json      # Metadane z cinemon
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

### cinemon
**Odpowiada za:**
- Tworzenie projektów Blender VSE
- Implementacja trybów animacji (beat-switch, energy-pulse, multi-pip)
- Generowanie keyframes na podstawie analizy audio
- Renderowanie finalnego video

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
beatrix analyze recording_20240115_120000/extracted/Microphone.m4a
# Tworzy:
recording_20240115_120000/
└── analysis/
    └── Microphone_analysis.json

# 4. cinemon tworzy projekt Blender
cinemon-blend-setup recording_20240115_120000 --animation-mode beat-switch
# Tworzy:
recording_20240115_120000/
└── blender/
    ├── recording_20240115_120000.blend
    └── render/
        └── recording_20240115_120000_final.mp4

# 5. medusa uploaduje video
medusa upload recording_20240115_120000/blender/render/recording_20240115_120000_final.mp4 --config upload_config.json
# Tworzy:
recording_20240115_120000/
└── uploads/
    └── upload_results.json
```

## 5. Walidacja Danych

Każdy pakiet powinien walidować swoje wejście:

- **obsession**: Sprawdza czy plik .mkv istnieje i jest czytelny
- **beatrix**: Waliduje format audio, sprawdza minimalną długość
- **cinemon**: Weryfikuje obecność metadata.json i plików w extracted/
- **medusa**: Sprawdza rozmiar pliku, format video, obecność konfiguracji

## 6. Wersjonowanie Formatów

Każdy format JSON zawiera pole `"version"` pozwalające na:
- Migrację starych formatów
- Zachowanie kompatybilności wstecznej
- Jasną komunikację o zmianach w formacie