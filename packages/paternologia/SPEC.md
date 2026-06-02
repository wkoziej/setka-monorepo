# Paternologia - Specyfikacja Projektu

## 1. Cel Projektu

Aplikacja webowa do zarządzania konfiguracjami urządzeń muzycznych MIDI dla poszczególnych utworów.
Główny kontroler: **PACER** (do 6 przycisków, każdy może wykonać do 6 akcji).

## 2. Model Danych

### 2.1 Urządzenia (devices.yaml)

```yaml
devices:
  - id: boss
    name: "Boss RC-600"
    description: "Loop Station"
    action_types:
      - preset
      - cc

  - id: ms
    name: "Elektron Model:Samples"
    description: "Sampler/Sequencer"
    action_types:
      - pattern

  - id: freak
    name: "Arturia MicroFreak"
    description: "Synthesizer"
    action_types:
      - preset
```

### 2.2 Utwór (songs/*.yaml)

```yaml
# songs/w-ciszy.yaml
song:
  id: w-ciszy
  name: "W ciszy"
  author: "Wojtek"
  created: 2024-12-14
  notes: "Ballada, tempo 72 BPM"

# Ustawienia początkowe urządzeń
devices:
  boss:
    preset: 1
    preset_name: "W ciszy"
  ms:
    pattern: "A0"
  freak:
    preset: 51
    preset_name: "W ciszy Pad"

# Konfiguracja przycisków PACER (lista, max 6)
pacer:
  - name: "Start"
    actions:
      - device: boss
        type: preset
        value: 1
        label: "W ciszy"
      - device: ms
        type: pattern
        value: "A0"
      - device: freak
        type: preset
        value: 51
        label: "W ciszy"
      - device: boss
        type: cc
        cc: 1
        label: "Play/Rec"

  - name: "Verse"
    actions:
      - device: ms
        type: pattern
        value: "A1"
      - device: boss
        type: cc
        cc: 1
        label: "Play/Rec"
```

### 2.3 Typy Akcji

| Typ | Parametry | Przykład |
|-----|-----------|----------|
| `preset` | `value`, `label` (opcjonalny) | Zmiana presetu na urządzeniu |
| `pattern` | `value` | Zmiana patternu (M:S) |
| `cc` | `cc`, `value` (domyślnie 127), `label` | Wysłanie MIDI CC |

## 3. Architektura

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Web)                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │ Song List │  │Song Editor│  │  PACER View   │   │
│  └───────────┘  └───────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                  │
│  ┌───────────┐  ┌───────────┐                       │
│  │ Songs API │  │Devices API│
│  └───────────┘  └───────────┘                       │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   Storage (YAML)                     │
│  data/                                              │
│  ├── devices.yaml                                   │
│  └── songs/                                         │
│      ├── w-ciszy.yaml                              │
│      └── inny-utwor.yaml                           │
└─────────────────────────────────────────────────────┘
```

### 3.1 Stack Technologiczny

| Warstwa | Technologia |
|---------|-------------|
| Backend | Python 3.12 + FastAPI |
| Frontend | HTMX + Jinja2 templates |
| Storage | YAML files |
| Styling | TailwindCSS (CDN) |
| Package manager | uv |

### 3.2 Dlaczego HTMX?

- Prosty interfejs bez potrzeby SPA
- Szybki development
- Minimalna ilość JavaScript
- Idealne do CRUD aplikacji

## 4. API Endpoints

### Songs

| Method | Endpoint | Opis |
|--------|----------|------|
| GET | `/` | Lista utworów (główna strona) |
| GET | `/songs/{id}` | Widok utworu z konfiguracją PACER |
| GET | `/songs/{id}/edit` | Formularz edycji |
| POST | `/songs` | Utwórz nowy utwór |
| PUT | `/songs/{id}` | Aktualizuj utwór |
| DELETE | `/songs/{id}` | Usuń utwór |

### Devices

| Method | Endpoint | Opis |
|--------|----------|------|
| GET | `/devices` | Lista urządzeń |
| GET | `/api/devices` | JSON z urządzeniami (dla formularzy) |


## 5. Interfejs Użytkownika

### 5.1 Strona Główna (Lista Utworów)

```
┌────────────────────────────────────────────────────┐
│  PATERNOLOGIA                        [+ Nowy utwór]│
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ W ciszy                              [Edytuj]│ │
│  │ Boss: preset 1 | M:S: A0 | Freak: preset 51 │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ Inny utwór                           [Edytuj]│ │
│  │ Boss: preset 5 | M:S: B2 | Freak: preset 12 │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 5.2 Widok Utworu (Konfiguracja PACER)

```
┌────────────────────────────────────────────────────┐
│  ← Powrót    W CISZY                     [Edytuj] │
├────────────────────────────────────────────────────┤
│                                                    │
│  USTAWIENIA POCZĄTKOWE                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │  BOSS   │  │   M:S   │  │  FREAK  │           │
│  │ pres. 1 │  │ patt.A0 │  │ pres.51 │           │
│  │"W ciszy"│  │         │  │"W ciszy"│           │
│  └─────────┘  └─────────┘  └─────────┘           │
│                                                    │
│  PACER (2 przyciski)                             │
│  ┌────────┐ ┌────────┐                           │
│  │   #1   │ │   #2   │                           │
│  │ Start  │ │ Verse  │                           │
│  ├────────┤ ├────────┤                           │
│  │Boss→1  │ │M:S→A1  │                           │
│  │M:S→A0  │ │Boss CC1│                           │
│  │Freak→51│ │        │                           │
│  │Boss CC1│ │        │                           │
│  └────────┘ └────────┘                           │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 5.3 Edycja Utworu

```
┌────────────────────────────────────────────────────┐
│  ← Anuluj    EDYCJA: W CISZY            [Zapisz] │
├────────────────────────────────────────────────────┤
│                                                    │
│  Nazwa: [W ciszy____________]                     │
│  Notatki: [Ballada, tempo 72 BPM____]            │
│                                                    │
│  USTAWIENIA POCZĄTKOWE                            │
│  Boss preset: [1___] nazwa: [W ciszy____]        │
│  M:S pattern: [A0__]                              │
│  Freak preset:[51__] nazwa: [W ciszy Pad]        │
│                                                    │
│  PACER                            [+ Dodaj przycisk]│
│  ┌─────────────────────────────────────────────┐ │
│  │ #1: [Start_____]                       [🗑️]│ │
│  ├─────────────────────────────────────────────┤ │
│  │ + Dodaj akcję                               │ │
│  │ [Boss ▼] [preset ▼] [1__] [W ciszy__] [🗑️]│ │
│  │ [M:S  ▼] [pattern▼] [A0_]            [🗑️]│ │
│  │ [Freak▼] [preset ▼] [51_] [W ciszy__] [🗑️]│ │
│  │ [Boss ▼] [cc     ▼] [1__] [Play/Rec_] [🗑️]│ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ #2: [Verse_____]                       [🗑️]│ │
│  ├─────────────────────────────────────────────┤ │
│  │ + Dodaj akcję                               │ │
│  │ [M:S  ▼] [pattern▼] [A1_]            [🗑️]│ │
│  │ [Boss ▼] [cc     ▼] [1__] [Play/Rec_] [🗑️]│ │
│  └─────────────────────────────────────────────┘ │
│                                                    │
└────────────────────────────────────────────────────┘
```

## 6. Struktura Projektu

```
paternologia/
├── pyproject.toml
├── README.md
├── SPEC.md                 # ta specyfikacja
│
├── src/
│   └── paternologia/
│       ├── __init__.py
│       ├── main.py         # FastAPI app
│       ├── models.py       # Pydantic models
│       ├── storage.py      # YAML read/write
│       └── routers/
│           ├── __init__.py
│           ├── songs.py
│           ├── devices.py
│           └── export.py
│
├── templates/
│   ├── base.html
│   ├── index.html          # lista utworów
│   ├── song.html           # widok utworu
│   ├── song_edit.html      # edycja utworu
│   └── partials/
│       ├── song_card.html
│       ├── pacer_button.html
│       └── action_row.html
│
├── static/
│   └── style.css           # customowe style
│
├── data/
│   ├── devices.yaml
│   └── songs/
│       └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_storage.py
    └── test_api.py
```

## 7. Kolejność Implementacji

1. **Faza 1: Fundament**
   - Inicjalizacja projektu (uv, pyproject.toml)
   - Modele Pydantic
   - Storage layer (YAML read/write)
   - Testy jednostkowe

2. **Faza 2: Backend**
   - FastAPI app setup
   - Songs CRUD endpoints
   - Devices endpoint

3. **Faza 3: Frontend**
   - Base template z HTMX
   - Lista utworów
   - Widok utworu (PACER visualization)
   - Formularz edycji

4. **Faza 4: Polish**
   - Styling (TailwindCSS)
   - Walidacja formularzy

## 8. Uruchomienie

```bash
# Instalacja
uv sync

# Development
uv run fastapi dev src/paternologia/main.py

# Produkcja
uv run fastapi run src/paternologia/main.py
```

## 9. Przyszłe Rozszerzenia (poza scope)

- Drag & drop kolejności przycisków
- MIDI preview (symulacja wysyłania)
- Setlisty (grupowanie utworów)
- Dark mode
- PWA (offline)
