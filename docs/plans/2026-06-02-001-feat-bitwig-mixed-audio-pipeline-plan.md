---
title: "feat: Bitwig jako etap miksu w pipelinie teledysku"
type: feat
status: completed
date: 2026-06-02
origin: docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md
deepened: 2026-06-02
---

# feat: Bitwig jako etap miksu w pipelinie teledysku

## Overview

Wstawiamy **Bitwig jako ręczny etap post-produkcji audio** pomiędzy nagraniem a analizą.
Po nagraniu Wojtas miksuje/wyrównuje głośności w Bitwigu i eksportuje dopracowany **master mix**
do ustalonego katalogu w strukturze nagrania (`mixed/`). Od tego momentu **Beatrix analizuje ten
master, a Cinemon używa go jako finalnego audio klipu** — zamiast surowego audio wyciągniętego
z OBS. Dryf audio↔wideo koryguje się ręcznie w Blenderze (poza pipelinem).

Zmiana jest celowo mała (wariant **„chude MVP"** wybrany po przeglądzie planu): Beatrix nie wymaga
zmian, a my **nie ruszamy współdzielonego resolvera ścieżek ani `MediaDiscovery`**. Realna praca to
(1) kanoniczny katalog `mixed/` w `setka-common`, (2) jawne wskazanie Cinemonowi mastera przez
`--main-audio` **ścieżką absolutną** (resolver bez zmian — działa dziś) oraz (3) drobna,
**master-aware** poprawka wyboru pliku analizy w Cinemonie, by nie użyć nieaktualnej analizy.
**Cymatic pozostaje poza zakresem.** Dryf audio↔wideo koryguje się ręcznie w Blenderze.

## Problem Frame

Dziś pipeline teledysku (OBSession → Fermata → Beatrix → Cinemon → Blender) analizuje i wkleja
do klipu **surowe audio z OBS** — bez szansy na poprawę jakości. Cel: jakość post-produkcji
audio przez ręczny miks w Bitwigu, którego eksport napędza dalszy pipeline. Pełny opis intencji
i decyzji produktowych: origin doc
(`docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md`).

## Requirements Trace

- **R1.** Struktura nagrania ma kanoniczny katalog `mixed/` na eksport audio z Bitwiga (master;
  gotowy też na stemy) — przez `RecordingStructureManager` (see origin: R1).
- **R2.** Beatrix analizuje master mix z Bitwiga (wskazanie istniejącego CLI na plik w `mixed/`)
  (see origin: R2).
- **R3.** Cinemon używa master miksu z Bitwiga jako finalnego audio klipu; wideo dalej z
  OBSession (see origin: R3).
- **R4.** Dryf audio↔wideo kompensowany ręcznie w Blenderze; brak auto-sync w pipelinie
  (see origin: R4).
- **R5.** Workflow udokumentowany w wiki (`Post-prod teledysk` + sekcja eksportu `Bitwig Studio`,
  ta druga już zrobiona) (see origin: R5).
- **R6. (odroczone)** Layout `mixed/` gotowy na stemy per-instrument bez przebudowy; pełne
  targetowanie per-ścieżka = osobna faza (see origin: R6).

## Scope Boundaries

- **Bez** automatycznej synchronizacji audio/wideo i bez wyrównywania OBS-audio vs Bitwig-audio.
- **Bez** automatyzacji eksportu w Bitwigu (ręczne `File → Export Audio`) i bez DAWproject.
- **Bez** pełnego targetowania per-stem teraz (R6 odroczone).
- **Bez** zmian w orkiestracji nagrywania (domena planu midi-recording-orchestration).
- **Bez** zmian w Beatrix (CLI już przyjmuje dowolną ścieżkę — potwierdzone w researchu).
- **Bez** zmian we współdzielonym resolverze ścieżek (`_resolve_relative_paths`) ani w
  `MediaDiscovery` — mastera wskazujemy jawnie ścieżką absolutną (wariant A po przeglądzie planu).
- **Cymatic poza zakresem** — dalej konsumuje audio/analizę z `extracted/` (ma własny resolver,
  nie używa `MediaDiscovery`); użycie mastera z `mixed/` w cymatic to przyszła faza.

## Context & Research

### Relevant Code and Patterns

- **`packages/common/src/setka_common/file_structure/specialized/recording.py`** — klasa
  `RecordingStructureManager` (od linii 54). Stałe `EXTRACTED_DIRNAME`/`BLENDER_DIRNAME`/
  `ANALYSIS_DIRNAME` (l. 58–60), dataclass `RecordingStructure` (pole `extracted_dir`),
  `get_structure()` (63–95), `create_structure()` (98–122), wzorzec `ensure_analysis_dir()`
  (228–265) i `ensure_blender_dir()` (183–225). **Wzór dodania katalogu = mirror tych metod.**
- **`packages/common/src/setka_common/utils/files.py`** — `MediaDiscovery` (30–178);
  **niezmieniany w tym planie**. Uwaga: `__init__` twardo wymaga istnienia `extracted/`
  (`FileNotFoundError`), a `validate_structure()` wymaga audio w `extracted/` → `extracted/`
  pozostaje warunkiem wstępnym (OBSession zawsze je produkuje).
- **`packages/common/src/setka_common/config/yaml_config.py`** — `_resolve_relative_paths()`
  (440–504): **ścieżka absolutna `main_audio` zwracana bez zmian (l. 463–464)** → mastera z
  `mixed/` wskazujemy absolutnie, **bez ruszania resolvera**. (Goła nazwa dalej → `extracted/`.)
- **`packages/cinemon/src/cinemon/config/cinemon_config_generator.py`** —
  `generate_config_from_preset()` (82–96) bierze `main_audio` z override lub
  `discovery.detect_main_audio()`. **Wybór analizy (186–191) używa `analysis_files[0]` —
  posortowane alfabetycznie → tu leży P0:** przy współistnieniu starej `*_analysis.json` z
  `master_analysis.json` może trafić w nieaktualny plik. To miejsce poprawki w Unit 2.
- **`packages/cinemon/src/cinemon/cli/blend_setup.py`** — opcja `--main-audio` (162–166),
  przekazanie jako override (287–295).
- **`packages/beatrix/src/beatrix/cli/click_cli.py`** — `analyze(audio_file, output_dir, …)`
  (46–109): `audio_file` to dowolna istniejąca ścieżka, `output_dir` tworzony, wynik
  `{stem}_analysis.json` (78–80). **Zero zmian.**
- **`packages/common/src/setka_common/file_structure/types.py`** — `AUDIO` (l. 22) zawiera
  `.wav`/`.flac` → eksport Bitwiga jest natywnie akceptowany.

### Institutional Learnings

- Workflow testów Setka: uruchamiać pytest **po ścieżce** i używać `uv sync --all-packages`;
  pełne `uv run pytest` bywa zepsute (z pamięci projektu). Weryfikację jednostek wyrażono jako
  uruchomienie testów konkretnego pakietu po ścieżce.

### External References

- Bitwig Userguide — Exporting Audio (`File → Export Audio`: per-track + Project Master) —
  potwierdza wykonalność eksportu mastera i stemów; wiki `Bitwig Studio` zaktualizowane.

## Key Technical Decisions

- **Katalog `mixed/` jako kanoniczne miejsce eksportu** (a nie reużycie `extracted/`): oddziela
  „surowe źródła z OBS" od „dopracowanego miksu z Bitwiga"; czytelne dla człowieka; naturalnie
  pomieści przyszłe stemy (`mixed/stems/`).
- **Master wskazywany jawnie, ścieżką absolutną** w `--main-audio` (wariant A): zero zmian we
  współdzielonym resolverze (`yaml_config.py:463-464` już zwraca absolutną ścieżkę bez zmian).
  Eliminuje ryzyko regresji `extracted/` i klasę bugów z auto-discovery (cymatic, separator w
  zwracanej ścieżce, przypadkowy plik w `mixed/`). Koszt: trzeba podać ścieżkę absolutną.
- **Master-aware wybór analizy w Cinemonie (P0 fix):** zamiast `analysis_files[0]` (sortowane)
  Cinemon wyprowadza oczekiwaną nazwę analizy ze stemu `main_audio` (`master.wav` →
  `master_analysis.json`) i preferuje ją; brak dopasowania → dotychczasowe zachowanie. Bez tego
  nieaktualna `*_analysis.json` z poprzedniego runu cicho rozjeżdża animacje z dźwiękiem.
- **Cymatic poza zakresem** — ma własny resolver (`AudioValidator().detect_main_audio(extracted_dir)`
  + `{stem}_analysis.json`), nie korzysta z `MediaDiscovery`; douczenie go `mixed/` to przyszła faza.
- **Beatrix bez zmian** — wskazujemy CLI na master, output do `analysis/`.
- **Sync poza kodem** — dryf koryguje człowiek w Blenderze; **założenie do weryfikacji: relacja to
  stały offset, nie narastający clock drift** (patrz Open Questions / Risks).

## Open Questions

### Resolved During Planning

- *Czy Beatrix/Cinemon wymagają zmian kodu?* — Beatrix: nie. Cinemon: jedyna zmiana to
  master-aware wybór pliku analizy (P0 fix); **brak** zmian w `MediaDiscovery`/resolverze.
- *Zakres handoffu (przegląd planu)* — wariant A „chude MVP": master wskazywany jawnie ścieżką
  absolutną; auto-discovery i zmiana resolvera odrzucone jako nadmiarowe wobec celu i ryzykowne
  dla shared code.
- *Nazwa konwencji katalogu* — `mixed/` (master jako `mixed/master.wav`, stemy w przyszłości w
  `mixed/stems/`).
- *Rola audio z OBS* — `extracted/` pozostaje warunkiem wstępnym (OBSession je produkuje) i
  źródłem wideo; finalne audio bierzemy z mastera wskazanego jawnie.
- *Format pliku* — WAV (i FLAC) są już w dozwolonych rozszerzeniach `AUDIO`.
- *Cymatic* — poza zakresem (własny resolver na `extracted/`); douczenie `mixed/` = przyszła faza.

### Deferred to Implementation

- Dokładne nazwy metod/pól (`ensure_mixed_dir`, `mixed_dir`) — do ustalenia przy mirrorze
  istniejących metod.
- Projekt drugiej fazy (R6): Beatrix per-stem (wiele wejść) i mapowanie stem→strip w Cinemon —
  osobny plan; wtedy też ergonomia (auto-discovery `mixed/`) i objęcie cymatic.

### Needs Validation (przed poleganiem na „no-sync")

- [Affects R4][Needs research] Zmierzyć offset audio↔wideo na początku i końcu jednego pełnego,
  długiego nagrania. Jeśli różnica head-vs-tail jest niezerowa (narastający drift), **pojedynczy
  offset w Blenderze nie wystarczy** — wtedy ręczna korekta wymaga retime/stretch, co zmienia
  trudność i sens odłożonego „parametru offsetu".

## Implementation Units

- [x] **Unit 1: Katalog `mixed/` w RecordingStructureManager**

**Goal:** Dodać kanoniczny katalog `mixed/` do struktury nagrania (master teraz, miejsce na stemy).

**Requirements:** R1, R6 (gotowość layoutu)

**Dependencies:** brak

**Files:**
- Modify: `packages/common/src/setka_common/file_structure/specialized/recording.py`
- Test: `packages/common/tests/test_recording_structure.py`

**Approach:**
- Dodać stałą `MIXED_DIRNAME = "mixed"` obok istniejących (l. ~58–60).
- Rozszerzyć dataclass `RecordingStructure` o pole `mixed_dir: Path`.
- Uzupełnić `get_structure()` (zbudowanie `mixed_dir`) i `create_structure()` (`mkdir`).
- Dodać `ensure_mixed_dir(recording_dir)` w stylu `ensure_analysis_dir()` (walidacja pustej
  ścieżki, `mkdir(parents=True, exist_ok=True)`, te same wyjątki `InvalidPathError`/
  `DirectoryCreationError`).
- Layout docelowy: `mixed/master.wav` (+ przyszłe `mixed/stems/`).

**Patterns to follow:** `ensure_analysis_dir()` (recording.py:228–265), `ensure_blender_dir()`
(183–225); stałe i pola dataclass jak `ANALYSIS_DIRNAME`/`analysis_dir`.

**Test scenarios:**
- Happy path: `get_structure(video)` zwraca `mixed_dir == recording_dir/"mixed"` bez tworzenia
  katalogu.
- Happy path: `create_structure(video)` tworzy `mixed/` obok `extracted/`, `analysis/`, `blender/`.
- Happy path: `ensure_mixed_dir(recording_dir)` tworzy katalog i jest idempotentne (drugie
  wywołanie nie rzuca).
- Edge case: pusta/niepoprawna `recording_dir` → `InvalidPathError` (jak w istniejących testach).
- Edge case: stała `MIXED_DIRNAME == "mixed"` (test wartości stałych, wzór l. 388–394).

**Verification:** Testy `packages/common/tests/test_recording_structure.py` (uruchamiane po
ścieżce dla pakietu `common`) przechodzą; `RecordingStructure` ma `mixed_dir`, a
`create_structure` materializuje `mixed/`.

---

- [x] **Unit 2: Master-aware wybór pliku analizy w Cinemonie (P0 fix)**

**Goal:** Gdy podano `main_audio` (np. absolutna ścieżka do `mixed/master.wav`), Cinemon ma
wybrać **analizę pasującą do mastera** (`master_analysis.json`), a nie pierwszy alfabetycznie plik
w `analysis/`. Bez tego nieaktualna analiza poprzedniego runu cicho rozjeżdża animacje z dźwiękiem.

**Requirements:** R2, R3, R4

**Dependencies:** Unit 1 (konwencja `mixed/`), ale technicznie niezależny od niej w kodzie

**Files:**
- Modify: `packages/cinemon/src/cinemon/config/cinemon_config_generator.py` (`_build_config_from_preset`,
  blok auto-wykrycia analizy l. ~186–191)
- Test: `packages/cinemon/tests/` (test generatora configu — dopasować do istniejącego pliku
  testów `cinemon_config_generator`)

**Approach:**
- W bloku wyboru analizy: jeśli znane jest `main_audio`, wyprowadzić oczekiwaną nazwę
  `f"{Path(main_audio).stem}_analysis.json"` i jeśli taki plik jest wśród
  `discovery.discover_analysis_files()` — wybrać go (jako `analysis/<nazwa>`).
- Fallback (brak dopasowania lub brak `main_audio`): **dotychczasowe** zachowanie
  (`analysis_files[0]`), więc istniejące nagrania działają bez zmian.
- **Brak** zmian w `MediaDiscovery` i `_resolve_relative_paths` (wariant A). Master wskazywany
  przez `--main-audio` ścieżką absolutną → resolver zwraca ją bez zmian (`yaml_config.py:463-464`).
- Beatrix bez zmian: `beatrix analyze /abs/…/mixed/master.wav /abs/…/analysis/` daje
  `analysis/master_analysis.json`.

**Patterns to follow:** istniejący blok `discover_analysis_files()` w
`cinemon_config_generator.py` (186–191); `Path(...).stem` jak w Beatrix (`click_cli.py:78–80`).

**Test scenarios:**
- Happy path: `main_audio` stem = `master`, w `analysis/` są `master_analysis.json` **oraz**
  stara `main_audio_analysis.json` → wybrana zostaje `analysis/master_analysis.json` (rdzeń P0).
- Happy path: `main_audio` stem = `master`, w `analysis/` tylko `master_analysis.json` → wybrana.
- Edge case: `main_audio` podane, ale brak `{stem}_analysis.json` → fallback do `analysis_files[0]`
  (zachowanie jak dziś), bez wyjątku.
- Edge case (regresja): `main_audio` nie podane (auto-detekcja) → wybór analizy identyczny jak
  przed zmianą.
- Edge case: `analysis/` puste → analiza `None`/pominięta jak dziś (bez wyjątku).

**Verification:** Testy `cinemon` (po ścieżce) przechodzą; dla nagrania, gdzie współistnieją stara
i master-analiza, generator wpina `analysis/master_analysis.json`; ścieżki bez `main_audio` lub
bez dopasowania zachowują dotychczasowy wybór.

---

- [x] **Unit 3: Dokumentacja workflow post-prod z Bitwigiem**

**Goal:** Opisać ręczny krok miksu + konwencję `mixed/` tak, by workflow był powtarzalny.

**Requirements:** R5

**Dependencies:** Unit 1, Unit 2 (opisujemy realne zachowanie: jawne `--main-audio` + master-aware analiza)

**Files:**
- Modify: `~/dev/music-box-wiki/wiki/workflows/Post-prod teledysk.md` (dodać etap „Miks w
  Bitwigu → eksport do `mixed/`" przed Beatrix; zaznaczyć ręczną kompensację dryfu w Blenderze)
- Modify: `~/dev/music-box-wiki/wiki/software/Paternologia.md` (poprawić lokalizację:
  `~/dev/paternologia` → `packages/paternologia` po PR #30) oraz wzmianki w workflowach, jeśli są
- Modify: `CLAUDE.md` (sekcja „Complete Pipeline Workflow" — dodać krok eksportu z Bitwiga do
  `mixed/` i wskazania Beatrix/Cinemon na master)

**Approach:**
- Workflow: po ekstrakcji OBSession → **ręczny miks w Bitwigu** → `File → Export Audio` mastera
  do `mixed/master.wav` → `beatrix analyze /abs/…/mixed/master.wav /abs/…/analysis/` →
  `cinemon-blend-setup … --main-audio /abs/…/mixed/master.wav` (**ścieżka absolutna**) → render;
  offset audio/wideo ustawiany ręcznie w Blenderze.
- Zaznaczyć: stemy (`mixed/stems/`), auto-discovery i targetowanie per-ścieżka to przyszła faza (R6).
- Sekcja eksportu w `Bitwig Studio.md` jest już dodana — tylko podlinkować z workflow.
- **`~/dev/music-box-wiki` to osobne repo git** (poza monorepo i poza CI) — edycje commitować/PR-ować
  niezależnie; tu tylko opisujemy, co zmienić.

**Patterns to follow:** styl i schema wiki (frontmatter `last_updated`, linki `[[…]]`) wg
`music-box-wiki/CLAUDE.md`; istniejący `Post-prod teledysk.md`.

**Test scenarios:** brak (dokumentacja). Weryfikacja przez przegląd treści.

**Verification:** `Post-prod teledysk` pokazuje etap Bitwig→`mixed/` i ręczną kompensację dryfu;
lokalizacja paternologii poprawiona; przykład w `CLAUDE.md` używa `mixed/master.wav`.

## System-Wide Impact

- **Interaction graph:** Unit 1 (nowa stała/pole w `RecordingStructureManager`) jest czysto
  addytywne. Unit 2 dotyka **tylko** `cinemon_config_generator` (wybór analizy) — z fallbackiem do
  obecnego zachowania. **Shared resolver/`MediaDiscovery` nieruszane** → brak wpływu na innych
  konsumentów.
- **Cymatic:** świadomie nieobjęty — ma własny resolver na `extracted/` + `{stem}_analysis.json`;
  nie korzysta z `MediaDiscovery`, więc ta zmiana go nie dotyka (ani nie psuje, ani nie pomaga).
- **Error propagation:** brak `mixed/` / brak `--main-audio` → ścieżki fallback działają jak dziś,
  nie błąd. Brak dopasowanej master-analizy → fallback `analysis_files[0]`.
- **State lifecycle risks:** brak — katalog addytywny; `ensure_mixed_dir` idempotentne.
- **API surface parity:** Unit 2 zachowuje wsteczną zgodność (brak `main_audio` lub brak
  dopasowania → dotychczasowy wybór) — pokryte testem regresji.
- **Integration coverage:** kluczowy test — generacja configu Cinemona, gdy w `analysis/`
  współistnieją stara i master-analiza (Unit 2).

## Risks & Dependencies

- **Nieaktualna analiza (P0)** — przy współistnieniu starej `*_analysis.json` z master-analizą
  Cinemon mógłby wpiąć złą; mitygacja: master-aware wybór analizy (Unit 2) + test współistnienia.
- **Drift vs offset** — „no-sync" zakłada stały offset; jeśli to narastający clock drift,
  pojedynczy ręczny offset w Blenderze nie wyrówna head i tail długiego nagrania; mitygacja:
  zmierzyć head-vs-tail na jednym pełnym nagraniu **przed** poleganiem na tej decyzji
  (Open Questions → Needs Validation).
- **Higiena `analysis/`** — przy re-renderach w `analysis/` zbierają się stare pliki; master-aware
  wybór to adresuje, ale warto w dokumentacji zalecić czyszczenie nieaktualnych analiz.
- **Zależność od capture w Bitwigu** — istnienie mastera zakłada działający miks/capture
  (plan midi-recording-orchestration); przy braku mastera pipeline działa jak dziś (graceful).
- **Wiki poza repo monorepo** — edycje w `~/dev/music-box-wiki` to osobne repo git; commit/PR
  tam niezależnie (poza CI monorepo).

## Documentation / Operational Notes

- Aktualizacja wiki (`Post-prod teledysk`, `Paternologia` lokalizacja) i `CLAUDE.md` „Complete
  Pipeline Workflow" — w Unit 3.
- Brak migracji danych, brak flag, brak rolloutu — zmiana addytywna i opt-in (działa tylko gdy
  pojawi się `mixed/`).

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md](docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md)
- Related code: `setka_common/file_structure/specialized/recording.py`,
  `setka_common/utils/files.py`, `setka_common/config/yaml_config.py`,
  `cinemon/config/cinemon_config_generator.py`, `beatrix/cli/click_cli.py`
- Related plans: `docs/plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md`,
  `docs/plans/2026-05-31-002-feat-recording-song-timeline-plan.md`
- External docs: Bitwig Userguide — Exporting Audio (https://www.bitwig.com/userguide/latest/exporting_audio/)
