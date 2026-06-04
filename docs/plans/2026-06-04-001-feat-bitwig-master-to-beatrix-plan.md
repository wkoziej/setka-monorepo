---
title: "feat: Bitwig master/stems → analiza beatrix jednym kliknięciem"
type: feat
status: active
date: 2026-06-04
origin: docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md
deepened: 2026-06-04
---

# feat: Bitwig master/stems → analiza beatrix jednym kliknięciem

## Overview

Domykamy „ostatnią milę" pipeline'u audio: po wyeksportowaniu zmiksowanego mastera
z Bitwig do `mixed/master.wav`, jedno kliknięcie „Analizuj" w fermacie ma uruchomić
analizę beatrix na masterze (i ewentualnych stemach z `mixed/stems/`), produkując po
jednej `analysis/{stem}_analysis.json` na plik. Dziś „Analizuj" patrzy tylko do
`extracted/`, filtruje wyłącznie `.m4a`, bierze pierwszy plik i cicho failuje w UI.

Zmiana ma trzy warstwy: (1) kanoniczny katalog `bitwig/` w strukturze nagrania jako
dom na projekt Bitwig, (2) świadomy `mixed/` resolver źródeł + tryb katalogowy w
beatrix iterujący po plikach, (3) fermata wołająca to jednym wywołaniem i pokazująca
błąd w UI. cinemon jest już „master-aware" — strona konsumenta jest gotowa.

## Problem Frame

Po dostrojeniu utworu w Bitwig droga dźwięku do analizy beatrix jest ręczna i
zawodna. Istniejący przycisk „Analizuj" (fermata → beatrix przez subprocess) jest
zahardkodowany na `extracted/` + `.m4a` + pierwszy plik, więc polerowanego
`mixed/master.wav` nie zobaczy, a gdy nie ma czego analizować — błąd ginie we
frontendzie. Wojtas chce minimum roboty teraz, ale otwartą drogę do analizy
poszczególnych ścieżek (stemów) pod przyszły per-strip targeting w cinemon.
(see origin: docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md)

## Requirements Trace

- R1. `RecordingStructureManager` zyskuje kanoniczny `bitwig/` (obok
  `extracted/`/`mixed/`/`analysis/`/`blender/`) jako dom na projekt Bitwig (Save As).
- R2. Master powstaje przez Bitwig Export Audio → `mixed/master.wav`; stemy
  (opcjonalnie) → `mixed/stems/*.wav`. Konwencja operatorska; kod ma ją respektować.
- R3. „Analizuj" (beatrix + fermata) iteruje po audio w `mixed/` (master + `stems/`),
  jedna `analysis/{stem}_analysis.json` per plik; preferuje `mixed/` nad `extracted/`
  (fallback do `extracted/`, gdy `mixed/` **nie ma plików audio LUB nie istnieje**).
  Logika iteruje, więc n=1 (master) działa dziś, a stemy później bez zmian w kodzie.
- R4. „Analizuj" pokazuje błąd w UI zamiast cicho failować, gdy nie ma czego
  analizować.
- R5. Render w fermacie (SetupRender) celuje `--main-audio` w `mixed/master.wav`
  (fallback `extracted/`), żeby cinemon faktycznie wybrał `master_analysis.json` bez
  ręcznego podawania ścieżki. *(Rozszerzenie zakresu wynikłe z review — domyka
  pipeline end-to-end; bez tego analiza mastera mogłaby zostać pominięta przy renderze.)*

## Scope Boundaries

- Bez watchera / daemona — świadomie odrzucone.
- Bez skryptowania Bitwig / controller extension / automatycznego eksportu
  (potwierdzone niewykonalne). Export Audio zostaje ręcznym krokiem w GUI.
- Bez auto-kopiowania z podfolderów projektu Bitwig (`master-recordings/`, `bounce/`).
- Bez zmian w **kodzie cinemon** — selekcja master-aware (`{stem}_analysis.json`) już
  istnieje; **nie ruszamy** `MediaDiscovery` ani `_resolve_relative_paths`. Spięcie
  realizujemy po stronie fermaty (SetupRender podaje `--main-audio` na master, R5/Unit 5).
- Bez utwardzania fallbacku cinemon `analysis_files[0]` — świadomie poza zakresem; przy
  wielu stemach domyślny wybór bez `--main-audio` pozostaje zależny od kolejności sortu
  (patrz Risks). Spięcie przez R5 (jawny `--main-audio` na master) to omija.
- Per-strip *targeting* animacji w cinemon to przyszła robota; tu odblokowujemy tylko
  *analizę* poszczególnych ścieżek.
- Korekta dryfu audio/wideo zostaje ręczna w Blenderze.

## Context & Research

### Relevant Code and Patterns

- **setka-common** `packages/common/src/setka_common/file_structure/specialized/recording.py`
  - Blok stałych (l. 58–62): `EXTRACTED_DIRNAME`, `BLENDER_DIRNAME`, `ANALYSIS_DIRNAME`,
    `MIXED_DIRNAME` — tu dochodzi `BITWIG_DIRNAME = "bitwig"`.
  - `@dataclass RecordingStructure(MediaStructure)` (l. 22–52), pola `extracted_dir`,
    `mixed_dir` — dochodzi `bitwig_dir: Path`. `exists()` (l. 29) celowo ignoruje
    katalogi opcjonalne — **nie dodawać tam bitwig**.
  - `get_structure()` (l. 64–99) buduje ścieżki (nie tworzy); `create_structure()`
    (l. 101–127) robi `mkdir(parents=True, exist_ok=True)` dla `extracted`/`mixed`.
  - `ensure_mixed_dir()` (l. 272–314) — dokładny szablon do sklonowania na
    `ensure_bitwig_dir()` (guard `InvalidPathError`, `mkdir(exist_ok=True)`, wrap
    `DirectoryCreationError`). Siostry: `ensure_analysis_dir` (233–270),
    `ensure_blender_dir` (187–230).
  - Helpery analizy już są: `get_analysis_file_path` (316–341, `{stem}_analysis.json`),
    `find_audio_analysis` (343–361). Prymityw skanu audio:
    `setka_common.utils.files.find_files_by_type(dir, MediaType.AUDIO)` (zwraca
    posortowaną, case-insensitive listę).
- **beatrix** `packages/beatrix/src/beatrix/core/audio_validator.py`
  - `AudioValidator.detect_main_audio(extracted_dir, specified_audio=None)` (l. 31–64);
    `find_audio_files(extracted_dir)` (l. 66–82) — wrapper na
    `find_files_by_type`; wyjątki `NoAudioFileError`/`MultipleAudioFilesError`
    (`beatrix/exceptions.py`). Parametr nazywa się `extracted_dir`, ale to dowolny
    katalog — można go wskazać na `mixed/` bez zmian sygnatury.
  - CLI `packages/beatrix/src/beatrix/cli/click_cli.py` — `analyze(audio_file,
    output_dir, beat_division, min_onset_interval)` (l. 46–108), **per plik**,
    nazewnictwo `{audio_file.stem}_analysis.json` (l. 78–80), błędy przez
    `click.ClickException`. Entry-point: `beatrix = "beatrix.cli.analyze_audio:main"`
    w `pyproject.toml`, gdzie `analyze_audio.main()` deleguje do `click_cli.main()`
    (grupa `click`). Dodanie subkomendy do tej grupy **nie wymaga** zmiany `pyproject.toml`.
- **fermata** (subprocess seam, nie bridge):
  - `packages/fermata/src-tauri/src/services/process_runner.rs` →
    `run_beatrix_analyze(recording_path, audio_file)` (l. 27–40): hardkoduje
    `extracted/`, woła `uv run --package beatrix beatrix analyze <audio_path>
    <recording_path/analysis>`. Wzorce sióstr: `run_cinemon_render` itp. (43–89),
    `execute_command` → `ProcessResult{success,stdout,stderr,exit_code}` (126–150).
  - `packages/fermata/src-tauri/src/commands/operations.rs` → `NextStep::Analyze`
    (l. 138–181): hardkoduje `extracted/` (140), filtruje `.m4a` (154), bierze
    `audio_files[0]` (178), ale **zwraca** `Err(...)` przy braku plików (164–176).
    Komendy zwracają `Result<String, String>` (konwencja całego repo).
  - Rejestracja komend: `packages/fermata/src-tauri/src/lib.rs` (`generate_handler!`,
    l. 17–32) — nowe komendy trzeba dopisać.
  - Status po analizie: `services/status_detector.rs::has_analysis_files` (l. 89+) —
    dowolny `.json` w `analysis/` → `RecordingStatus::Analyzed`; wiele JSON-ów per-plik
    zadziała bez zmian.
  - **Cichy fail jest we froncie:** `packages/fermata/src/components/RecordingList.tsx`
    (l. 207–223) po `runSpecificStep` robi tylko `refreshRecordings()` na `setTimeout`
    i nie czyta `operationState.error`. Hook
    `packages/fermata/src/hooks/useRecordings.ts`: `runSpecificStep` (173–203) łapie
    błąd do `operationState.error`, ale `refreshRecordings` (74–94) w `catch` podstawia
    **mock data** i zeruje `error` — dodatkowe maskowanie. Wzorzec do naśladowania:
    `runSetupRenderWithPreset` (205–237) zapisuje `output: \`Error: ${msg}\``.

### Institutional Learnings

- `docs/solutions/` nie ma wpisów dot. file-structure/beatrix/fermata (tylko audio
  hardware). Najbliższy precedens: **`docs/plans/2026-06-02-001-feat-bitwig-mixed-audio-pipeline-plan.md`**
  (completed) — dodanie `mixed/` przeszło dokładnie wg wzorca 4 punktów + matrycy 5
  testów; `mkdir(parents=True, exist_ok=True)` → idempotentne, „purely additive".
- Master-aware selekcja w cinemon już zaimplementowana
  (`cinemon/config/cinemon_config_generator.py:186-201`) — po zapisaniu
  `analysis/master_analysis.json` cinemon ją podchwyci bez zmian.
- Gotcha higieny: nieaktualne `*_analysis.json` kumulują się w `analysis/` —
  master-aware łagodzi zły wybór, ale warto rozważyć czyszczenie stale (odłożone).
- **Test gotcha (MEMORY):** uruchamiać pytest **po ścieżce**, nie pełne
  `uv run pytest` (zepsute); `uv sync --all-packages`.

### External References

- Brak nowego — research Bitwig (brak headless renderu, brak akcji Export w API, brak
  per-project ścieżki eksportu) zrobiony w origin brainstorm.

## Key Technical Decisions

- **Logika „preferuj mixed/ + iteruj" po stronie Pythona, nie Rust.** Resolver źródeł
  w setka-common (`RecordingStructureManager`), tryb katalogowy w beatrix CLI; fermata
  woła jednym wywołaniem. Rationale: DRY (wiedza o strukturze już jest w
  setka-common), testowalność (pytest/CliRunner zamiast testów Rust subprocessu),
  prostszy Rust, bezpośrednio realizuje R3. Alternatywa „pętla w Rust" odrzucona —
  dublowałaby zbiór rozszerzeń audio i preferencję katalogów w drugim języku.
  Krawędź **beatrix → setka_common już istnieje** (`audio_validator.py` importuje
  `setka_common.utils.files`; setka-common to twarda zależność beatrix), więc resolver
  w setka-common nie tworzy nowej zależności międzypakietowej.
- **Nowa subkomenda `analyze-recording <katalog>`; istniejące `analyze <plik> <out>`
  pozostaje nietknięte.** Świadomie odrzucamy overload `analyze` rozpoznający
  plik-vs-katalog (dwuznaczna semantyka, footgun przy katalogu z jednym plikiem). Daje
  fermacie jednoznaczne wywołanie i utrzymuje zgodność wstecz dokumentowanego
  `beatrix analyze` (CLAUDE.md/wiki). Dodanie subkomendy do istniejącej grupy `click`
  **nie wymaga** zmiany `pyproject.toml`.
- **`bitwig/` tworzony zachłannie w `create_structure` (jak `mixed/`)** + lazy
  `ensure_bitwig_dir` dla istniejących nagrań. Rationale: spójność z `mixed/`, kanoniczny
  dom na Save As gotowy od razu. Świadomie akceptujemy, że **żaden kod nie czyta**
  `bitwig/` — to celowy „reserved location"/afordancja dla operatora, nie wejście dla
  automatyki; brak katalogu w starych nagraniach jest nieszkodliwy (analiza czyta
  `mixed/`/`extracted/`).
- **Fallback `extracted/` zachowany** — stare nagrania bez `mixed/` analizują się jak
  dotąd (zgodność wstecz, R3).
- **Cichy fail naprawiamy dwustronnie**, ale ciężar na froncie: Rust już zwraca `Err`;
  front musi go renderować i przestać maskować mockiem.

## Open Questions

### Resolved During Planning

- **Gdzie żyje pętla (CLI-dir vs loop-w-fermacie)?** → Python: resolver w setka-common
  + tryb katalogowy w beatrix CLI; fermata woła raz. (uzasadnienie wyżej)
- **Czy `bitwig/` tworzyć zachłannie?** → Tak, jak `mixed/`; + lazy `ensure_bitwig_dir`.
- **Czy stare nagrania wymagają migracji `bitwig/`?** → Nie; nic nie czyta `bitwig/`,
  brak katalogu jest nieszkodliwy. Resolver analizy gating-uje na `.exists()` `mixed/`.
- **Czy ruszać kod cinemon?** → Nie; master-aware selekcja już działa. Spięcie
  end-to-end robimy w fermacie (R5/Unit 5: SetupRender `--main-audio` → master).
- **Kształt trybu katalogowego beatrix?** → Nowa subkomenda `analyze-recording
  <katalog>` (nie overload `analyze`). Brak zmian w `pyproject.toml`.
- **Polityka kolizji `{stem}_analysis.json`?** → **Fail-fast**: gdy dwa źródła
  (np. `mixed/master.wav` i `mixed/stems/master.wav`) dałyby ten sam plik wyjściowy,
  przerwij z czytelnym błędem wskazującym kolidujące pliki — **bez cichego nadpisania**
  (zgodnie z FAIL FAST). Zalecana konwencja: unikalne nazwy stemów.

### Deferred to Implementation

- **Mapowanie nazw stemów → targety stripów w cinemon** — osobna przyszła robota
  (per-strip targeting), poza tym planem.
- **Czyszczenie stale `*_analysis.json`** przed zapisem nowych — czy kasować osierocone
  analizy nieodpowiadające źródłom z `mixed/`. Drobne; ocenić przy implementacji.
- **Czy resolver ma też zaglądać do `bitwig/<proj>/master-recordings|bounce/`** jako
  fallback — odłożone ułatwienie, poza MVP.

## Implementation Units

- [ ] **Unit 1: `bitwig/` w RecordingStructureManager**

**Goal:** Kanoniczny katalog `bitwig/` jako dom na projekt Bitwig — mirror wzorca `mixed/`.

**Requirements:** R1

**Dependencies:** Brak.

**Files:**
- Modify: `packages/common/src/setka_common/file_structure/specialized/recording.py`
- Test: `packages/common/tests/test_recording_structure.py`

**Approach:**
- Dodaj `BITWIG_DIRNAME = "bitwig"` do bloku stałych (l. 58–62).
- Dodaj pole `bitwig_dir: Path` do `RecordingStructure` (wzór: `mixed_dir`, l. 27).
  Nie dotykać `exists()`.
- W `get_structure()` zbuduj `bitwig_dir = project_dir / ...BITWIG_DIRNAME` i przekaż do
  konstruktora; w `create_structure()` dodaj `structure.bitwig_dir.mkdir(parents=True,
  exist_ok=True)` obok `mixed`.
- Sklonuj `ensure_mixed_dir` → `ensure_bitwig_dir` (ten sam guard + wrap wyjątków).

**Patterns to follow:** `MIXED_DIRNAME`/`mixed_dir`/`ensure_mixed_dir` w tym samym pliku;
matryca testów z planu 2026-06-02-001 (Unit 1).

**Test scenarios:**
- Happy path: `get_structure()` zwraca `bitwig_dir` jako ścieżkę, **nie tworząc** katalogu.
- Happy path: `create_structure()` materializuje `bitwig/` obok `extracted`/`mixed`.
- Happy path: `ensure_bitwig_dir(recording_dir)` tworzy `bitwig/` i zwraca Path.
- Edge case: `ensure_bitwig_dir` na istniejącym katalogu — idempotentne (drugie wywołanie OK).
- Error path: pusty/nieistniejący/`not is_dir` `recording_dir` → `InvalidPathError`.
- Happy path: `BITWIG_DIRNAME == "bitwig"` (test wartości stałej).

**Verification:** Testy `test_recording_structure.py` przechodzą (uruchom po ścieżce);
`create_structure` na świeżym `tmp_path` daje katalog `bitwig/`.

---

- [ ] **Unit 2: Resolver źródeł `mixed/`→`extracted/` w setka-common**

**Goal:** Jedno źródło prawdy o tym, które pliki audio analizować dla danego nagrania:
preferuj `mixed/` (master + `mixed/stems/`), fallback `extracted/`.

**Requirements:** R3

**Dependencies:** Brak (może powstać równolegle z Unit 1).

**Files:**
- Modify: `packages/common/src/setka_common/file_structure/specialized/recording.py`
- Test: `packages/common/tests/test_recording_structure.py`

**Approach:**
- Dodaj static helper, np. `find_analysis_audio_sources(recording_dir) -> list[Path]`:
  zbierz audio z `mixed/` **i osobno** z `mixed/stems/`. **Uwaga:** `find_files_by_type`
  jest **nierekurencyjne** (`iterdir`), więc trzeba **dwóch wywołań** (`mixed/` oraz
  `mixed/stems/`) i scalić wyniki — jedno wywołanie pominęłoby stemy.
- Fallback: jeśli `mixed/` **nie ma plików audio LUB nie istnieje** → skanuj `extracted/`.
  Gating na `.exists()` dla `mixed/`/`stems/`. Zwróć posortowaną, deterministyczną listę.
- **Polityka kolizji:** jeśli dwa źródła dałyby ten sam `{stem}_analysis.json`
  (np. `mixed/master.wav` + `mixed/stems/master.wav`), przerwij fail-fast z błędem
  wskazującym kolidujące pliki — bez cichego nadpisania.
- Stałe `MIXED_DIRNAME`/`EXTRACTED_DIRNAME` brane z managera, nie hardkodowane.
- **Nie** kierować `mixed/` przez `AudioValidator.detect_main_audio` — przy >1 pliku
  rzuca `MultipleAudioFilesError`; resolver to osobna ścieżka.

**Patterns to follow:** istniejące `find_audio_analysis`/`get_analysis_file_path`;
prymityw `find_files_by_type` z `setka_common.utils.files`.

**Test scenarios:**
- Happy path: tylko `mixed/master.wav` → zwraca `[master.wav]`.
- Happy path: `mixed/master.wav` + `mixed/stems/{a,b}.wav` → zwraca wszystkie trzy.
- Edge case: `mixed/` istnieje, ale **bez plików audio** (np. tylko `stems/` puste),
  `extracted/` ma pliki → fallback do `extracted/`.
- Edge case: `mixed/` nieobecne, `extracted/` ma pliki → fallback do `extracted/`.
- Edge case: oba puste/nieobecne → zwraca `[]` (bez wyjątku; decyzja „brak audio" wyżej).
- Edge case: mieszane rozszerzenia (`.wav`/`.flac`/`.m4a`) — wszystkie audio złapane,
  nie-audio pominięte; stemy z `mixed/stems/` dołączone (test nierekurencyjności).
- Error path: kolizja nazwy (`mixed/master.wav` + `mixed/stems/master.wav`) → fail-fast
  z błędem wskazującym oba pliki, bez nadpisania.
- Edge case: kolejność wyników deterministyczna (sort, case-insensitive).

**Verification:** Testy resolvera przechodzą; resolver zwraca master gdy obecny, a
stemy dokłada bez zmian w innym kodzie.

---

- [ ] **Unit 3: Tryb katalogowy/recording w beatrix CLI (iteracja per plik)**

**Goal:** beatrix analizuje wszystkie źródła nagrania jednym wywołaniem, pisząc
`analysis/{stem}_analysis.json` per plik; istniejący per-plikowy `analyze` bez zmian.

**Requirements:** R3

**Dependencies:** Unit 2 (resolver źródeł).

**Files:**
- Modify: `packages/beatrix/src/beatrix/cli/click_cli.py`
- Test: `packages/beatrix/tests/test_cli_click.py`
- (Bez zmian w `pyproject.toml` — subkomenda dochodzi do istniejącej grupy `click`.)

**Approach:**
- Dodaj **nową subkomendę `analyze-recording <recording_dir> [--beat-division ...]
  [--min-onset-interval ...]`** do grupy `cli` (nie overload `analyze`). Użyj
  `find_analysis_audio_sources(recording_dir)` z Unit 2, iteruj, dla każdego pliku
  zapisz `{stem}_analysis.json` do `analysis/` (reużyj nazewnictwa, l. 78–80). Gdy lista
  pusta → `ClickException` z czytelnym komunikatem (zasila R4 przez stderr subprocessu).
  Kolizja nazw → fail-fast (polityka z Unit 2/Open Questions).
- Przekaż `beat_division`/`min_onset_interval` do każdej analizy.
- Zachowaj single-file `analyze(<plik> <out>)` **bez zmian sygnatury**.

**Patterns to follow:** obecny `analyze()` (nazewnictwo outputu, obsługa błędów przez
`ClickException`); testy `TestClickCLI` z `CliRunner`.

**Test scenarios:** (przez `CliRunner` na `analyze-recording`)
- Happy path: katalog z `mixed/master.wav` → powstaje `analysis/master_analysis.json`.
- Happy path: `mixed/` z masterem + 2 stemami → 3 pliki `*_analysis.json`, po jednym na źródło.
- Edge case: `mixed/` puste, `extracted/` ma 1 plik → analiza z `extracted/` (fallback).
- Error path: brak audio w `mixed/` i `extracted/` → niezerowy exit + komunikat na stderr.
- Error path: kolizja nazw stemów → niezerowy exit + komunikat o kolizji, żaden plik nie nadpisany.
- Edge case: parametry `--beat-division`/`--min-onset-interval` propagują do każdej analizy.
- Regression: dotychczasowy `analyze <plik> <out>` działa jak wcześniej (sygnatura nietknięta).

**Execution note:** Zacznij od failującego testu CLI na trybie katalogowym (kontrakt
„N plików → N analiz").

**Verification:** `test_cli_click.py` zielone (po ścieżce); jedno wywołanie na katalogu
generuje komplet analiz; single-file ścieżka bez regresji.

---

- [ ] **Unit 4: fermata — jedno wywołanie beatrix na nagraniu + błąd w UI**

**Goal:** „Analizuj" woła beatrix raz na całym nagraniu (drop hardkodu `extracted/`/`.m4a`/
`[0]`), a błąd jest widoczny w UI zamiast cicho ginąć.

**Requirements:** R3, R4

**Dependencies:** Unit 3 (tryb katalogowy beatrix).

**Files:**
- Modify: `packages/fermata/src-tauri/src/services/process_runner.rs`
- Modify: `packages/fermata/src-tauri/src/commands/operations.rs`
- Modify: `packages/fermata/src/components/RecordingList.tsx`
- Test: inline `#[cfg(test)]` w `operations.rs`/`process_runner.rs`;
  `packages/fermata/src/components/RecordingList.test.tsx`

**Approach (Rust):**
- `run_beatrix_analyze`: zmień na wywołanie `beatrix analyze-recording <recording_path>`
  (bez parametru `audio_file`, bez budowania `extracted/<plik>`). Propaguj
  `ProcessResult.stderr` jako `Err` przy `!success` (wzór `run_next_step`).
- `NextStep::Analyze` w `operations.rs`: usuń listowanie `extracted/`/filtr `.m4a`/`[0]`;
  wywołaj raz `run_beatrix_analyze(recording.path)`; brak audio/kolizję sygnalizuje
  beatrix (stderr → `Err(String)`). Zachowaj konwencję `Result<String, String>`.

**Approach (frontend) — zawężony (finding #2):**
- **Cichy fail żyje w `RecordingList.tsx`, nie w hooku.** `runSpecificStep` już zapisuje
  realny błąd do `operationState.error`; wystarczy go **przeczytać i wyrenderować** po
  operacji (wzór `runSetupRenderWithPreset` → `Error: ${msg}`).
- **NIE ruszamy `refreshRecordings`/mock-fallbacku** w `useRecordings.ts` — to celowy
  tryb dev (brak Tauri), osobna ścieżka niezwiązana z błędem analyze. Modyfikacja byłaby
  scope creepem ryzykującym regresję offline-dev.

**Patterns to follow:** `Result<String,String>` + `map_err(format!)` (recordings.rs);
test `test_missing_dependencies` (operations.rs 386–495) jako wzór asercji `Err`;
`uv_path: "echo"` do stubowania subprocessu; Vitest + `@testing-library` w istniejących
`*.test.tsx`.

**Test scenarios:**
- Happy path (Rust): nagranie z `mixed/master.wav`, stub `uv`=`echo` → komenda zwraca
  `Ok`, woła `beatrix analyze-recording <recording_path>` (nie `extracted/<plik>`).
- Error path (Rust): brak audio (beatrix zwraca niezerowy exit/stderr) → komenda zwraca
  `Err` z komunikatem ze stderr.
- Integration (Rust): wywołanie nie zawiera już filtra `.m4a` ani `audio_files[0]` —
  cała robota selekcji jest po stronie beatrix.
- Happy path (front): udana analiza → brak błędu, lista odświeżona.
- Error path (front): `runSpecificStep` ustawia `operationState.error` → komunikat
  błędu **widoczny** w `RecordingList` (test renderu błędu).

**Verification:** `cargo test` w `src-tauri` zielone; Vitest zielony; ręcznie: klik
„Analizuj" na nagraniu z `mixed/master.wav` tworzy `analysis/master_analysis.json`, a
na nagraniu bez audio pokazuje czytelny błąd.

---

- [ ] **Unit 5: SetupRender celuje `--main-audio` w master (spięcie do cinemon)**

**Goal:** Render w fermacie podaje cinemon master z `mixed/`, żeby został wybrany
`master_analysis.json` bez ręcznego `--main-audio`. Domyka pipeline end-to-end.

**Requirements:** R5

**Dependencies:** Unit 1–4 logicznie po (master już analizowany), ale zmiana w
SetupRender jest niezależna technicznie.

**Files:**
- Modify: `packages/fermata/src-tauri/src/commands/operations.rs` (gałąź
  `NextStep::SetupRender`)
- Modify (jeśli rozdzielanie ścieżki): `packages/fermata/src-tauri/src/services/process_runner.rs`
  (`run_cinemon_generate_config`/`run_cinemon_render`)
- Test: inline `#[cfg(test)]` w `operations.rs`

**Approach:**
- W `NextStep::SetupRender` rozwiąż `main_audio`: jeśli istnieje `mixed/master.wav` →
  podaj go jako `--main-audio` (ścieżka **absolutna**, bo cinemon master-aware oczekuje
  absolutnej); w przeciwnym razie zachowaj dotychczasowe zachowanie (`extracted/` /
  `AppConfig.main_audio_file`). To jedyna potrzebna zmiana — kod cinemon zostaje.
- Świadomie **nie** utwardzamy fallbacku `analysis_files[0]` w cinemon (poza zakresem);
  jawny `--main-audio` na master omija problem kolejności sortu przy stemach.

**Patterns to follow:** istniejąca gałąź `NextStep::Analyze`/`SetupRender` w
`operations.rs`; `run_cinemon_*` w `process_runner.rs`; `AppConfig.main_audio_file`
(recordings.rs) jako dotychczasowe źródło domyślne.

**Test scenarios:**
- Happy path: istnieje `mixed/master.wav` → SetupRender przekazuje `--main-audio` ze
  ścieżką absolutną do `mixed/master.wav`.
- Edge case: brak `mixed/master.wav` → zachowane dotychczasowe rozwiązanie audio
  (`extracted/`/config) — brak regresji.
- Integration: przy obecnym `analysis/master_analysis.json` przekazany master prowadzi
  cinemon do wyboru `master_analysis.json` (weryfikacja przez argument `--main-audio`,
  bez uruchamiania Blendera).

**Verification:** `cargo test` zielone; ręcznie: po „Analizuj" + render na nagraniu z
`mixed/master.wav` cinemon użył `master_analysis.json` (nie pierwszego z brzegu).

## System-Wide Impact

- **Interaction graph:** `RecordingStructureManager` używany przez wszystkie pakiety —
  zmiana czysto addytywna (nowy katalog/helper), istniejące pola/metody nietknięte.
  fermata `NextStep::Analyze` → `process_runner` → `beatrix analyze-recording` →
  `analysis/*.json` → `status_detector.has_analysis_files` → `RecordingStatus::Analyzed`
  (działa z wieloma JSON-ami). Następnie `NextStep::SetupRender` → `--main-audio` na
  `mixed/master.wav` (Unit 5) → cinemon wybiera `master_analysis.json` (już master-aware).
- **Error propagation:** beatrix (ClickException/exit≠0) → `ProcessResult.stderr` →
  `Err(String)` w komendzie Tauri → `operationState.error` (hook już to ustawia) →
  **render w `RecordingList`** (jedyne brakujące ogniwo, które naprawiamy; hook/mock
  nietknięte).
- **State lifecycle risks:** nieaktualne `*_analysis.json` w `analysis/` (stale) — łagodzi
  master-aware selekcja cinemon + jawny `--main-audio` (Unit 5); czyszczenie odłożone.
  Domyślny fallback cinemon `analysis_files[0]` przy wielu stemach bez `--main-audio`
  pozostaje zależny od sortu — świadomie poza zakresem, omijany przez Unit 5.
- **API surface parity:** single-file `beatrix analyze <plik> <out>` zachowany; nowa
  subkomenda `analyze-recording <katalog>` dodatkowa. Brak zmian w kodzie cinemon/medusy.
- **Integration coverage:** testy Rust ze stubem `uv=echo` weryfikują wywołanie i
  propagację błędu; testy Python (CliRunner + tmp_path) weryfikują „N plików → N analiz".

## Risks & Dependencies

- **Stare nagrania bez `mixed/`** — fallback `extracted/` utrzymuje zgodność wstecz.
- **`bitwig/` nieobecny w starych nagraniach** — nieszkodliwe; nic go nie czyta.
- **Sekwencja:** Unit 4 zależy od Unit 3 (`analyze-recording`), Unit 3 od Unit 2
  (resolver). Unit 1 i Unit 5 niezależne technicznie (Unit 5 logicznie po analizie).
- **Stemy „za darmo" są warunkowe:** kolizja nazw rozwiązana fail-fast (bez utraty
  danych), ale domyślny wybór cinemon przy wielu stemach bez `--main-audio` zależy od
  sortu — pełne per-stem targeting to przyszła robota poza tym planem.
- **Test gotcha:** pytest po ścieżce (`uv run --package <pkg> pytest <path>`), nie pełne
  `uv run pytest`; `uv sync --all-packages`.

## Documentation / Operational Notes

- Po wdrożeniu zaktualizować CLAUDE.md (sekcja file-structure: dodać `bitwig/`) i
  `~/dev/music-box-wiki` (workflow „Post-prod teledysk": Export Audio → `mixed/`, klik
  „Analizuj" analizuje master + stemy).
- Kandydat na wpis `docs/solutions/`: gotcha „fermata Analizuj — extracted-only + `.m4a`
  + cichy fail we froncie".

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md](docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md)
- Precedens: `docs/plans/2026-06-02-001-feat-bitwig-mixed-audio-pipeline-plan.md` (completed)
- Kod: `recording.py` (`ensure_mixed_dir`), `audio_validator.py`, `click_cli.py`,
  `operations.rs::NextStep::Analyze`, `process_runner.rs::run_beatrix_analyze`,
  `useRecordings.ts`, `RecordingList.tsx`, `cinemon_config_generator.py:186-201`
