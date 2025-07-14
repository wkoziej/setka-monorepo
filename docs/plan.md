# Setka - Integrated Media Processing Pipeline

## Cel Projektu

Setka łączy dwa specjalistyczne narzędzia do automatyzacji przetwarzania i publikowania mediów:

- **Obsession**: Automatyczna ekstrakcja źródeł z nagrań OBS i renderowanie w Blenderze
- **Medusa**: Automatyczne uploadowanie na platformy hostingowe i publikowanie w mediach społecznościowych

## Workflow Docelowy

```
1. Nagranie OBS → 2. Przetwarzanie (Obsession) → 3. Decyzja o publikacji → 4. Upload (Medusa)
```

### Szczegółowy przepływ:

1. **Nagranie w OBS Studio**
   - Nagrywanie z metadanymi scen
   - Zapisywanie do struktury katalogów

2. **Przetwarzanie w Obsession**
   - Automatyczna ekstrakcja źródeł video/audio
   - Analiza dźwięku (beat detection)
   - Renderowanie w Blender VSE
   - Status: `rendered` w pliku `status.json`

3. **Przegląd i decyzja (ręczna)**
   - Przegląd wyrenderowanego materiału
   - Decyzja o publikacji
   - Przygotowanie metadanych (tytuł, opis, tagi)

4. **Upload przez Medusa**
   - CLI: `medusa upload "recording-name" --title "..." --privacy public`
   - Upload na YouTube/inne platformy
   - Status: `uploaded` w pliku `status.json`

## Architektura Techniczna

### Aktualna struktura projektów:
```
setka/
├── docs/                   # Dokumentacja projektu
├── obsession/             # Git submodule - przetwarzanie mediów
├── medusa/               # Git submodule - upload i publikowanie  
├── CLAUDE.md            # Instrukcje dla Claude Code
└── .gitmodules         # Konfiguracja submodułów
```

### Planowana struktura z wspólną biblioteką:
```
setka/
├── docs/                   # Dokumentacja
├── setka-common/          # Wspólna biblioteka (nowy moduł)
│   ├── file_structure.py  # Zarządzanie strukturą plików
│   ├── models.py          # Wspólne modele danych  
│   ├── exceptions.py      # Hierarchia błędów
│   ├── tasks.py          # Zarządzanie zadaniami
│   └── config.py         # Zarządzanie konfiguracją
├── obsession/            # Używa setka-common
├── medusa/              # Używa setka-common
└── setka-cli/           # Główny CLI (przyszłość)
```

## Obszary Do Implementacji

### Faza 1: Podstawowa Integracja (Tydzień 1)
- [ ] **Medusa CLI** - implementacja brakującego interfejsu komend
- [ ] **Status tracking** - minimalne pliki `status.json` w obsession
- [ ] **File structure sharing** - wspólne zarządzanie ścieżkami

### Faza 2: Wspólna Biblioteka (Tydzień 2) 
- [ ] **setka-common** - wyciągnięcie wspólnego kodu
- [ ] **Unified models** - `MediaFile`, `ProcessingResult`
- [ ] **Task management** - współdzielony `TaskManager`
- [ ] **Error handling** - wspólna hierarchia `SetkaError`

### Faza 3: Zaawansowana Integracja (Tydzień 3)
- [ ] **setka-cli** - nadrzędny CLI dla całego pipeline
- [ ] **Configuration management** - ujednolicony system konfiguracji
- [ ] **Recording browser** - interfejs do przeglądania nagrań (opcjonalnie)

## Decyzje Architektoniczne

### 1. **Status Tracking**
- **Minimalistyczne podejście**: tylko `{"status": "rendered", "upload_status": "ready"}`
- **Lokalizacja**: w katalogu każdego nagrania jako `status.json`
- **Uzasadnienie**: unikamy duplikacji informacji które wynikają ze struktury plików

### 2. **Code Sharing Strategy**
- **setka-common** jako osobny moduł Python
- **Progresywna migracja**: zaczynamy od file structure, potem models, na końcu task management
- **Uzasadnienie**: unikamy dużego refactoringu, zachowujemy działające funkcjonalności

### 3. **CLI Design**
- **Medusa CLI** jako pierwszy priorytet: `medusa upload "recording-name"`
- **setka-cli** jako przyszła nadrzędna komenda: `setka process-and-upload "recording-name"`
- **Uzasadnienie**: zaczynamy od prostego, rozwijamy w kierunku złożonego

### 4. **Dependency Management**
- **Git submodules** dla obsession i medusa
- **uv** jako package manager dla wszystkich części
- **Python 3.12+** jako wymagana wersja

## Oczekiwane Korzyści

### Dla użytkownika (Wojtas):
1. **Usprawnienie workflow**: od nagrania do publikacji w kilku komendach
2. **Konsystentność**: ujednolicone podejście do błędów, statusów, konfiguracji
3. **Skalowalność**: łatwe dodawanie nowych platform, formatów, workflow

### Dla rozwoju:
1. **Mniejsza duplikacja kodu**: wspólne utilities i modele
2. **Łatwiejsze testowanie**: ujednolicone podejście do testów
3. **Lepsze utrzymanie**: centralne miejsce dla wspólnych funkcjonalności

## Ryzyka i Mitigacje

### Ryzyko: Złożoność integracji
- **Mitigacja**: fazowe podejście, zaczynamy od prostych rzeczy
- **Fallback**: każdy projekt nadal działa niezależnie

### Ryzyko: Breaking changes w submodułach  
- **Mitigacja**: semantic versioning, testy integracyjne
- **Fallback**: pinowanie wersji submodułów

### Ryzyko: Over-engineering
- **Mitigacja**: focus na praktyczne potrzeby, nie teoretyczne abstrakcje
- **Zasada**: implementujemy tylko to co rzeczywiście będzie używane

## Pierwsze Kroki

1. ✅ **Setup repozytorium**: GitHub repo dla setka
2. 🔄 **Medusa CLI**: implementacja `medusa upload` command
3. ⏳ **Status integration**: dodanie `status.json` do obsession workflow
4. ⏳ **File structure sharing**: pierwszy wspólny kod w setka-common

---

**Status**: W fazie planowania i setup'u  
**Ostatnia aktualizacja**: 2025-07-12  
**Responsible**: Wojtas + Claude Code