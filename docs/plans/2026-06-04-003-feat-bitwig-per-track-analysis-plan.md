---
title: "feat: Analiza per-track z bitwig/ + manifest odkrywania dla cymatic/cinemon"
type: feat
status: completed
date: 2026-06-04
origin: docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md
deepened: 2026-06-04
---

# feat: Analiza per-track z bitwig/ + manifest odkrywania dla cymatic/cinemon

## Overview

Rozszerzamy istniejącą akcję „Analizuj" (fermata → `beatrix analyze-recording`),
żeby jednym kliknięciem analizowała **wszystkie ścieżki nagrania**, biorąc stemy z
hybrydowego źródła: preferuj polerowane `mixed/stems/`, a gdy ich brak — sięgnij po
**surowy multitrack capture leżący już w `bitwig/<…>/samples/`**. Każda ścieżka
dostaje znormalizowaną (sanityzowaną) nazwę i własną `analysis/<stem>_analysis.json`,
a całość spinamy nowym manifestem **`analysis/index.json`** — kontraktem odkrywania,
dzięki któremu cymatic i cinemon **enumerują i rozróżniają** analizy (master vs
per-track, czysta etykieta, ścieżka źródłowa) bez zgadywania po globie.

Punkt wyjścia: poprzedni, **zmergowany** plan
(`2026-06-04-001-feat-bitwig-master-to-beatrix-plan.md`) zbudował już: kanoniczny
katalog `bitwig/`, resolver `find_analysis_audio_sources` (mixed/ → fallback
extracted/), subkomendę `beatrix analyze-recording <dir>` oraz wywołanie jej z
fermaty jednym kliknięciem. **Ten plan jest czysto addytywny** względem tamtego —
nie przepisujemy działającej logiki, dokładamy warstwę „bitwig jako źródło stemów"
i warstwę odkrywania.

## Problem Frame

Operator nagrywa live wielościeżkowo do Bitwiga; surowe ścieżki lądują w
`bitwig/<projekt>/samples/` (np. `m_s-24.wav`, `track 4+git-24.wav`,
`track 5_6+mic+freak-24.wav`). To gotowy, izolowany per-instrument materiał idealny
do **wyzwalaczy animacji** (beat/onset/energy) — ale dziś „Analizuj" go nie widzi
(iteruje tylko `mixed/`), a nawet gdyby widział, surowe nazwy z sufiksem Bitwiga
(`-24`, `-25`) i znakami `+`/`/`/spacja są niewygodne, a żaden moduł nie ma jak
**odróżnić** mastera od ścieżki ani znaleźć „tej właściwej" analizy. Wojtas chce:
wcisnąć „Analizuj" mając katalog `bitwig/` → dostać analizy wszystkich ścieżek →
a cymatic/cinemon mają je łatwo znaleźć i rozróżnić.

**Model zapisu audio w Bitwigu (ustalony w trakcie planowania):** pliki w `samples/`
to **surowy capture z nagrywania**, niezależny od miksu. Dodanie efektu, zmiana
głośności/EQ/panoramy są **nieniszczące** — żyją w `.bwproject`, nie ruszają plików
w `samples/`. Przetworzony dźwięk powstaje wyłącznie przez ręczne **Export Audio**
(→ `mixed/`) albo destrukcyjne Bounce/Freeze. Stąd podział:
- **`mixed/master.wav`** (Export Audio) — ścieżka dźwiękowa klipu + globalne triggery.
- **`bitwig/…/samples/*.wav`** (surowe) — per-instrumentowe triggery animacji „za darmo".

(see origin: docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md,
docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md)

## Requirements Trace

- R1. „Analizuj" produkuje analizę **dla każdej ścieżki** nagrania, biorąc stemy z
  hybrydy: preferuj `mixed/stems/`, fallback do `bitwig/<…>/samples/`. Master z
  `mixed/master.wav` pozostaje osobnym, „master"-owym źródłem. Zero dodatkowej akcji
  operatora poza dotychczasowym kliknięciem (fermata już woła `analyze-recording`).
- R2. Nazwy analiz są **sanityzowane** ze stemu źródła (zdjęcie sufiksu Bitwiga
  `-NN`, normalizacja spacji/`+`/`/` → `_`), tak by `analysis/<clean>_analysis.json`
  były stabilne i bez znaków uwierających downstream. Kolizja sanityzowanych nazw →
  **fail-fast** (bez cichego nadpisania), spójnie z polityką poprzedniego planu.
- R3. Powstaje **manifest `analysis/index.json`** — kontrakt odkrywania: lista źródeł
  z `role` (`master`/`stem`), `origin` (`mixed`/`bitwig`/`extracted`), czystą
  `label`, względną ścieżką `source` i `analysis`. cymatic/cinemon mogą enumerować i
  **rozróżniać** analizy bez globowania ani zgadywania po nazwie.
- R4. setka-common udostępnia **mały reader manifestu** (typowane wejście kontraktu),
  by konsumenci czytali `index.json` jednolicie zamiast parsować JSON ad-hoc.
- R5. Zachowana **zgodność wstecz**: nagrania bez `bitwig/`/`mixed/stems/` analizują
  się jak dotąd (master z `mixed/`, ostateczny fallback `extracted/`); single-file
  `beatrix analyze <plik> <out>` i istniejące zachowanie `analyze-recording` (n=1
  master) bez regresji.

## Scope Boundaries

- **Bez zmian w konsumpcji** w cinemon/cymatic — nie wiążemy stripów/elementów wizualnych
  z konkretnymi analizami per-track. Dostarczamy tylko *analizy* + *kontrakt odkrywania*
  (manifest + reader). Pełny per-strip targeting w cinemon to osobna, przyszła robota
  (świadomie utrzymana granica z poprzednich brainstormów).
- **Bez zmian w kodzie Rust fermaty** — „Analizuj" już woła `beatrix analyze-recording
  <recording_path>` (poprzedni plan, Unit 4). Per-track analiza i manifest powstają po
  stronie Pythona, więc przycisk działa bez modyfikacji frontendu/backendu fermaty.
- **Bez parsowania `.bwproject`** dla ludzkich nazw ścieżek — odrzucone (format binarny,
  kruche, sprzęga z wersją Bitwiga). Nazwy bierzemy z nazw plików + sanityzacja. (Nazwy
  plików — `m_s`, `track 4+git`, `mic+freak` — i tak niosą sens.)
- **Bez watchera/daemona, bez skryptowania Bitwiga, bez auto-eksportu** — jak w origin.
- **Bez filtrowania „co jest nagraniem vs zaimportowanym samplem" w `samples/`** —
  na start analizujemy wszystkie audio w `samples/`; ewentualne wykluczanie
  bibliotecznych sampli odłożone (patrz Risks/Deferred).
- Korekta dryfu audio/wideo zostaje ręczna w Blenderze.

## Context & Research

### Relevant Code and Patterns

- **setka-common** `packages/common/src/setka_common/file_structure/specialized/recording.py`
  - Stałe (l. 63–64): `MIXED_DIRNAME = "mixed"`, `BITWIG_DIRNAME = "bitwig"` — już są.
  - `RecordingStructure.bitwig_dir` (l. 28), tworzony w `create_structure` (l. 125);
    `ensure_bitwig_dir` (l. 322+) — `bitwig/` istnieje jako kanoniczny dom.
  - **`find_analysis_audio_sources(recording_dir)` (l. 364–413)** — sedno do
    rozszerzenia. Dziś: zbiera `mixed/` + `mixed/stems/` (non-rekurencyjnie, dwa
    wywołania `find_files_by_type`), fallback `extracted/`, collision-check po
    `stem.lower()`, zwraca posortowaną listę. Wzorzec do utrzymania.
  - `get_analysis_file_path` (l. 415+) i `find_audio_analysis` — istniejące helpery
    nazewnictwa `{stem}_analysis.json`. `ensure_analysis_dir` — dom na `index.json`.
  - Prymityw skanu: `setka_common.utils.files.find_files_by_type(dir, MediaType.AUDIO)`
    — **nierekurencyjny** (`iterdir`), sort case-insensitive.
- **beatrix** `packages/beatrix/src/beatrix/cli/click_cli.py`
  - `analyze-recording` (l. 124–171): woła resolver, `ensure_analysis_dir`, pętla
    `_analyze_single_file(audio, analysis_dir, …)` (l. 60: nazwa
    `{audio_file.stem}_analysis.json`), błędy przez `ClickException`. Tu wchodzi:
    sanityzacja nazwy wyjścia + zapis `index.json` po pętli.
  - `analyze <plik> <out>` (l. 97) — **nie ruszać** (zgodność wstecz, R5).
  - Testy: `packages/beatrix/tests/test_cli_click.py` (`CliRunner`).
- **fermata** — `process_runner.rs::run_beatrix_analyze` woła
  `beatrix analyze-recording <recording_path>`; `commands/operations.rs::NextStep::Analyze`
  woła to raz; `services/status_detector.rs::has_analysis_files` liczy **dowolny** `.json`
  w `analysis/` → `Analyzed` (dojście `index.json` nieszkodliwe). **Bez zmian.**
- **Konsumenci (tylko do zrozumienia kontraktu — nie zmieniamy):**
  - cinemon `config/cinemon_config_generator.py:186-201` — master-aware: dobiera
    `analysis/<main_audio.stem>_analysis.json`.
  - cymatic `src/cymatic/cli.py` — `--analysis-file PATH` (jawnie) lub detekcja z
    `extracted/`; `analysis_loader.load_analysis(config)` czyta ścieżkę z konfiga.
  - Oba selekcjonują **po nazwie stem / jawnej ścieżce** — manifest `index.json`
    dostarcza tej nazwy/ścieżki w jednym miejscu (to jest „rozróżnianie").

### Institutional Learnings

- Precedens addytywnego rozszerzania struktury: `docs/plans/2026-06-02-001-...` i
  `2026-06-04-001-...` (oba completed) — `mkdir(exist_ok=True)`, „purely additive",
  matryca testów resolvera. Trzymać ten styl.
- `docs/solutions/` nie ma wpisów dot. file-structure/beatrix — kandydat na nowy wpis
  po wdrożeniu (gotcha: „bitwig/samples to surowy capture, niezależny od miksu").
- **Test gotcha (MEMORY):** pytest uruchamiać **po ścieżce**
  (`uv run --package <pkg> pytest <path>`), nie pełne `uv run pytest` (zepsute);
  `uv sync --all-packages`.

### External References

- Brak nowych. Model zapisu audio Bitwiga (capture vs Export Audio vs Bounce/Freeze)
  ustalony w trakcie planowania; udokumentowany w `~/dev/music-box-wiki` (Bitwig Studio).

## Key Technical Decisions

- **Hybryda jako tiery w resolverze, nie nowa komenda.** `find_analysis_audio_sources`
  rozbudowujemy w dwa tiery: (1) **master/mixed-root** = audio bezpośrednio w `mixed/`;
  (2) **stems** = `mixed/stems/` jeśli niepuste, **inaczej** `bitwig/…/samples/`.
  Łączymy, collision-check, sort. Ostateczny fallback `extracted/` zachowany. Rationale:
  jedno źródło prawdy o „co analizować", beatrix i fermata bez zmian sygnatur (R1, R5).
- **Sanityzacja nazwy przy wyznaczaniu pliku wyjściowego**, nie przy źródle (plików nie
  ruszamy). Czysty `label`/stem trafia do `<clean>_analysis.json` i do manifestu.
  Konsekwencja: konsumenci **nie** wyprowadzą nazwy analizy z surowej nazwy pliku —
  i właśnie dlatego potrzebny jest manifest jako bridge (spójne z wyborem „sanityzacja
  + manifest"). Master (`master.wav`) sanityzuje się do `master` (bez zmiany).
- **Manifest `analysis/index.json` jako kontrakt odkrywania** (nie zmiana nazewnictwa
  istniejących analiz poza sanityzacją). Pisany przez `analyze-recording` po pętli;
  zawiera `role`/`origin`/`label`/`source`/`analysis`. Rationale: cymatic/cinemon
  dostają stabilny, enumerowany spis „co jest dostępne i czym jest" bez globowania
  i bez wnioskowania po nazwie pliku (R3).
- **Reader manifestu w setka-common** (nie w każdym konsumencie osobno) — DRY, typowane
  wejście kontraktu; setka-common to wspólna twarda zależność (R4). Reader **rozwija**
  ścieżki względne do absolutnych (`recording_dir / value`) — to on, nie konsument,
  zna konwencję bazy (inaczej każdy konsument odtwarzałby tę samą sklejkę).
- **`analysis` jest jedynym poprawnym kluczem do pliku analizy.** Kontrakt jawnie mówi
  konsumentom: **nie** wyprowadzaj nazwy analizy z `main_audio` przez `<stem>_analysis.json`.
  Powód: sanityzacja rozjeżdża nazwę dla źródeł innych niż `master.wav` (np. surowy stem
  `track 4+git-24` → analiza `track_4_git_analysis.json`; derywacja po surowym stemie
  trafiłaby w pustkę i cinemon cicho spadłby na `analysis_files[0]`). **Master jest
  bezpieczny** (`sanitize("master") == "master"`), więc istniejąca master-aware selekcja
  cinemon działa bez zmian; ostrzeżenie dotyczy przyszłej selekcji per-stem.
- **Lokalizacja sampli Bitwiga elastyczna:** szukamy `samples/` w `bitwig/` — najpierw
  `bitwig/samples/`, potem jeden poziom `bitwig/*/samples/` (Save As do podkatalogu).
  Bez głębokiej rekursji (uniknięcie wciągnięcia niezwiązanego audio). Rationale: realne
  nagranie ma `bitwig/samples/`, ale `.bwproject` bywa zapisany w podkatalogu projektu.
- **Fail-fast na kolizji sanityzowanych nazw** (jak w poprzednim planie) — dwa źródła →
  ten sam `<clean>_analysis.json` → przerwij z czytelnym błędem wskazującym kolidujące
  pliki. Bez cichego nadpisania.

## Open Questions

### Resolved During Planning

- **Źródło stemów?** → Hybryda: `mixed/stems/` preferowane, fallback `bitwig/…/samples/`.
  Master nadal z `mixed/master.wav`.
- **Skąd sensowne nazwy?** → Sanityzacja nazw plików (bez parsowania `.bwproject`) +
  manifest `index.json` jako kontrakt odkrywania.
- **Zakres?** → Analizy per-track + manifest + reader. Bez wiązania konsumpcji
  (per-strip targeting) w cinemon/cymatic.
- **Czy fermata wymaga zmian?** → Nie; „Analizuj" już woła `analyze-recording`.
- **Czy ruszać master flow / single-file `analyze`?** → Nie; czysto addytywne (R5).
- **Baza ścieżek w manifeście i rozwijanie do absolutnych?** → `source` i `analysis` oba
  względne do `recording_dir` (z prefiksem katalogu); reader rozwija przez
  `resolved_analysis_path(recording_dir)`. (decyzja z walidacji architektonicznej)
- **Co konsument dostaje do walidacji zgodności ścieżek?** → `duration`+`sample_rate`
  w każdym wpisie manifestu (manifest samowystarczalny).
- **Lookup po etykiecie w readerze?** → Tak, `by_label(label)` jest częścią kontraktu.

### Deferred to Implementation

- **Filtrowanie `samples/`** — czy wykluczać zaimportowane/biblioteczne sample (nie-capture)
  z analizy. Na MVP analizujemy wszystkie audio w `samples/`; reguła wykluczeń odłożona.
- **Czyszczenie stale `*_analysis.json`/`index.json`** przy ponownym „Analizuj" gdy zmienił
  się zestaw źródeł — ocenić przy implementacji (czy nadpisywać/czyścić osierocone).
- **Dokładny kształt `role` przy fallbacku `extracted/`** (gdy brak `mixed/` i `bitwig/`) —
  proponowane `role: "main"`/`origin: "extracted"`; doprecyzować w testach.
- **Wersjonowanie schematu manifestu** (`version`) — start `1`; polityka ewolucji odłożona.

## High-Level Technical Design

> *Ilustruje zamierzony kształt rozwiązania i jest wskazówką do recenzji, nie specyfikacją
> implementacji. Implementujący traktuje to jako kontekst, nie kod do odtworzenia.*

**Tiery resolvera (źródła do analizy):**

```
find_analysis_audio_sources(recording_dir):
  master_tier = audio bezpośrednio w mixed/        # zwykle mixed/master.wav
  stems_tier  = audio w mixed/stems/  (jeśli niepuste)
                else audio w <bitwig samples dir>  (fallback)
  sources = master_tier + stems_tier
  if sources: collision-check(po sanitize(stem)); return sorted(sources)
  else: return sorted(audio w extracted/)          # zgodność wstecz
```

**Manifest `analysis/index.json` (kontrakt odkrywania; WSZYSTKIE ścieżki względne do
katalogu nagrania — jednolita baza dla `source` i `analysis`):**

```jsonc
{
  "version": 1,
  "sources": [
    { "role": "master", "origin": "mixed",  "label": "master",
      "source": "mixed/master.wav",
      "analysis": "analysis/master_analysis.json",
      "duration": 182.4, "sample_rate": 44100 },
    { "role": "stem",   "origin": "bitwig", "label": "m_s",
      "source": "bitwig/samples/m_s-24.wav",
      "analysis": "analysis/m_s_analysis.json",
      "duration": 182.4, "sample_rate": 44100 },
    { "role": "stem",   "origin": "bitwig", "label": "track_4_git",
      "source": "bitwig/samples/track 4+git-24.wav",
      "analysis": "analysis/track_4_git_analysis.json",
      "duration": 182.4, "sample_rate": 48000 }
  ]
}
```

Konsument (cymatic/cinemon, w przyszłej fazie) robi: wczytaj `index.json` → wybierz wpis
po `role`/`label` → użyj **`analysis` jako jedynego klucza** do pliku analizy (reader
rozwija względną ścieżkę do absolutnej). To jest cała „łatwość odnajdywania i rozróżniania".

**Dwie świadome decyzje kontraktu (z walidacji architektonicznej):**
- **Jednolita baza ścieżek:** `source` i `analysis` są oba względne do `recording_dir`
  (`analysis/<plik>`, nie goła nazwa) — jedna reguła rozwijania `recording_dir / value`
  działa dla obu i likwiduje klasę błędów asymetrii prefiksu.
- **`duration`/`sample_rate` w każdym wpisie** (beatrix już je emituje) — manifest jest
  samowystarczalny do walidacji zgodności master↔per-track (różne SR/długości stemów
  z `bitwig/samples/`) bez otwierania N plików JSON.

> **Uwaga dla przyszłej fazy konsumpcji:** `label` NIE jest gwarantowanym stabilnym
> identyfikatorem między uruchomieniami — zależy od nazwy pliku w Bitwigu. Per-strip
> targeting (wiązanie audio-stem ↔ wideo-strip) nie powinien budować trwałego mapowania
> na `label`; to przyszła robota i wymaga osobnego, stabilnego id (świadomie poza zakresem,
> YAGNI — nie dodajemy pustego pola `id` bez konsumenta).

## Implementation Units

- [ ] **Unit 1: `sanitize_stem_name` — czysta nazwa stemu**

**Goal:** Deterministyczna funkcja zamieniająca surową nazwę pliku Bitwiga na stabilny,
bezpieczny stem (label) dla nazwy analizy i manifestu.

**Requirements:** R2

**Dependencies:** Brak.

**Files:**
- Modify: `packages/common/src/setka_common/file_structure/specialized/recording.py`
  (lub nowy mały moduł `setka_common/utils/naming.py` jeśli czytelniej — decyzja przy
  implementacji; preferuj umieszczenie blisko resolvera)
- Test: `packages/common/tests/test_recording_structure.py` (lub `tests/test_naming.py`)

**Approach:**
- `sanitize_stem_name(name: str) -> str`: zdejmij rozszerzenie jeśli podano pełną nazwę
  (przyjmij już-stem lub pełną — ustalić), zdejmij **sufiks Bitwiga** `-<cyfry>` na końcu
  (`track 4+git-24` → `track 4+git`), zamień separatory/znaki problematyczne
  (spacja, `+`, `/`, `\`) na `_`, scal wielokrotne `_`, przytnij brzegowe `_`, lower-case
  opcjonalnie (ustalić — proponowane: zachować wielkość liter, tylko normalizacja znaków).
- Idempotentność: `sanitize(sanitize(x)) == sanitize(x)`.
- Pusty wynik (np. nazwa same znaki spec.) → fail-fast `ValueError` (czytelny komunikat).

**Patterns to follow:** styl pojedynczych helperów w `setka_common/utils/files.py`.

**Test scenarios:**
- Happy path: `"track 4+git-24"` → `"track_4_git"`.
- Happy path: `"m_s-24"` → `"m_s"`; `"track 5_6+mic+freak-24"` → `"track_5_6_mic_freak"`.
- Happy path: `"master"` → `"master"` (bez zmian; brak sufiksu liczbowego).
- Edge case: brak sufiksu `-NN` → tylko normalizacja znaków.
- Edge case: idempotentność (drugie wywołanie nie zmienia wyniku).
- Edge case: kropki/rozszerzenie w wejściu obsłużone zgodnie z ustaloną sygnaturą.
- Error path: nazwa redukująca się do pustego stringu → `ValueError`.

**Execution note:** Zacznij od failującego testu tabelarycznego (mapowania nazw realnych
z `bitwig/samples/`).

**Verification:** Testy zielone (po ścieżce); realne nazwy z nagrania mapują się czysto.

---

- [ ] **Unit 2: Lokalizator sampli Bitwiga + hybrydowy resolver źródeł**

**Goal:** `find_analysis_audio_sources` zwraca master z `mixed/` + stemy z
`mixed/stems/` **lub** (fallback) z `bitwig/…/samples/`, z collision-check po
sanityzowanym stemie. Zgodność wstecz zachowana.

**Requirements:** R1, R2, R5

**Dependencies:** Unit 1 (sanityzacja do collision-check).

**Files:**
- Modify: `packages/common/src/setka_common/file_structure/specialized/recording.py`
- Test: `packages/common/tests/test_recording_structure.py`

**Approach:**
- Dodaj `find_bitwig_sample_sources(recording_dir) -> list[Path]`: zlokalizuj katalog
  `samples/` w `bitwig/` — najpierw `bitwig/samples/`, w razie braku przeskanuj jeden
  poziom `bitwig/*/samples/`; zbierz audio przez `find_files_by_type(..., AUDIO)`
  (non-rekurencyjnie). Brak `bitwig/`/`samples/` → `[]`.
- Refaktor `find_analysis_audio_sources` na tiery (patrz High-Level Technical Design):
  master-tier = audio w `mixed/` (root); stems-tier = `mixed/stems/` jeśli niepuste,
  inaczej `find_bitwig_sample_sources(...)`. Połącz, **collision-check po
  `sanitize_stem_name(p.stem)`** (nie po surowym stemie), sort case-insensitive.
- Zachowaj ostateczny fallback `extracted/` (gdy master-tier i stems-tier puste).
- Stałe katalogów z managera (`MIXED_DIRNAME`/`BITWIG_DIRNAME`/`EXTRACTED_DIRNAME`),
  bez hardkodu. `"stems"` jak dziś (literał już w kodzie).

**Patterns to follow:** istniejące `find_analysis_audio_sources` (l. 364–413) i jego
collision-check; `find_files_by_type` non-rekurencyjne (dlatego osobne skany katalogów).

**Test scenarios:**
- Happy path: `mixed/master.wav` + `mixed/stems/{a,b}.wav` → master + 2 stemy (bitwig
  zignorowany, bo `mixed/stems/` niepuste).
- Happy path (nowy): `mixed/master.wav` + `mixed/stems/` puste/brak + `bitwig/samples/`
  z 3 wav → master + 3 stemy z bitwig.
- Happy path (czysto bitwig): brak `mixed/`, `bitwig/samples/` z N wav → N źródeł
  (master-tier pusty, stems-tier = bitwig). *(Uwaga: jeśli równolegle brak mastera,
  manifest oznaczy je `role: stem`.)*
- Edge case: `bitwig/<proj>/samples/` (jeden poziom zagnieżdżenia) wykryte.
- Edge case: `mixed/stems/` niepuste **wygrywa** nad `bitwig/samples/` (fallback nie odpala).
- Edge case: brak `mixed/` i `bitwig/`, `extracted/` ma pliki → fallback `extracted/`
  (zgodność wstecz).
- Edge case: wszystko puste/nieobecne → `[]`.
- Error path: dwa źródła sanityzują się do tej samej nazwy (np. `track 4+git-24.wav`
  i `track_4_git.wav`) → `ValueError` z oboma plikami, bez nadpisania.
- Edge case: kolejność deterministyczna (sort, case-insensitive).

**Verification:** Testy resolvera zielone; na realnym katalogu nagrania resolver zwraca
master + 6 ścieżek z `bitwig/samples/` gdy `mixed/stems/` puste.

---

- [ ] **Unit 3: beatrix `analyze-recording` — sanityzowane nazwy + zapis `index.json`**

**Goal:** Jedno wywołanie analizuje wszystkie źródła, pisząc `<clean>_analysis.json`
per ścieżka oraz manifest `analysis/index.json` z rolami/etykietami/ścieżkami.

**Requirements:** R1, R2, R3, R5

**Dependencies:** Unit 1 (sanityzacja), Unit 2 (resolver hybrydowy).

**Files:**
- Modify: `packages/beatrix/src/beatrix/cli/click_cli.py`
- Test: `packages/beatrix/tests/test_cli_click.py`
- (Bez zmian w `pyproject.toml`.)

**Approach:**
- W `analyze-recording`: dla każdego źródła wyznacz `label = sanitize_stem_name(stem)`
  i nazwę wyjścia `<label>_analysis.json` (zamiast surowego `{stem}_analysis.json`).
  Przekaż jawną nazwę wyjścia do `_analyze_single_file` (rozszerz o opcjonalny
  `output_name`/`label`, zachowując dotychczasowe zachowanie dla single-file `analyze`).
- Wyznacz `role`/`origin` per źródło z jego lokalizacji: w `mixed/` root → `master`/`mixed`;
  w `mixed/stems/` → `stem`/`mixed`; w `bitwig/…/samples/` → `stem`/`bitwig`; w `extracted/`
  → `main`/`extracted` (fallback). Zbieraj wpisy podczas pętli.
- Po pętli zapisz `analysis/index.json` (`version: 1`, `sources: [...]`). Pola wpisu:
  `role`/`origin`/`label`/`source`/`analysis` (**oba** `source` i `analysis` względne do
  `recording_dir`, z prefiksem katalogu — `analysis/<label>_analysis.json`, nie goła nazwa)
  oraz `duration`/`sample_rate` wzięte z właśnie wyliczonej analizy (beatrix je zwraca w
  JSON-ie). Zapis atomowy-ish (write + rename) opcjonalnie.
- Pustą listę źródeł i kolizję nadal sygnalizuj `ClickException` (zasila błąd w UI fermaty
  przez stderr — mechanizm z poprzedniego planu, bez zmian).

**Patterns to follow:** obecny `analyze-recording`/`_analyze_single_file` (l. 60, 124–171);
testy `CliRunner`; nazewnictwo `{stem}_analysis.json` jako baza.

**Test scenarios:** (przez `CliRunner`)
- Happy path: katalog z `mixed/master.wav` + `bitwig/samples/{m_s-24,track 4+git-24}.wav`
  (puste `mixed/stems/`) → powstają `master_analysis.json`, `m_s_analysis.json`,
  `track_4_git_analysis.json` **oraz** `index.json`.
- Integration: `index.json` ma 3 wpisy z poprawnymi `role` (`master` + 2× `stem`),
  `origin` (`mixed` + 2× `bitwig`), `label` (sanityzowane), względnymi z prefiksem
  `source`/`analysis` (`analysis/<label>_analysis.json`) oraz `duration`/`sample_rate`
  zgodnymi z wartościami z wygenerowanych analiz.
- Happy path: `mixed/stems/` niepuste → wpisy `origin: mixed`, bitwig pominięty.
- Edge case: fallback `extracted/` (brak `mixed/`/`bitwig/`) → wpisy `role: main`/`origin: extracted`.
- Error path: brak audio → niezerowy exit + komunikat (bez `index.json`).
- Error path: kolizja sanityzowanych nazw → niezerowy exit, żaden plik nie nadpisany,
  brak/niezmieniony `index.json`.
- Edge case: `--beat-division`/`--min-onset-interval` propagują do każdej analizy.
- Regression: single-file `analyze <plik> <out>` bez zmian (sygnatura/zachowanie).
- Regression: n=1 (sam `mixed/master.wav`) → `master_analysis.json` + `index.json`
  z jednym wpisem `role: master`.

**Execution note:** Zacznij od failującego testu kontraktu „N źródeł → N analiz +
poprawny index.json".

**Verification:** `test_cli_click.py` zielone; jedno wywołanie generuje komplet analiz
+ manifest; single-file bez regresji.

---

- [ ] **Unit 4: Reader manifestu w setka-common (kontrakt dla konsumentów)**

**Goal:** Typowane, jednolite czytanie `analysis/index.json`, by cymatic/cinemon (w
przyszłości) nie parsowały JSON ad-hoc.

**Requirements:** R4

**Dependencies:** Unit 3 (kształt manifestu ustalony) — może powstać równolegle do testów
Unit 3, byle schema była zgodna.

**Files:**
- Modify: `packages/common/src/setka_common/file_structure/specialized/recording.py`
  (lub dedykowany `setka_common/file_structure/analysis_index.py`)
- Test: `packages/common/tests/test_recording_structure.py` (lub `tests/test_analysis_index.py`)

**Approach:**
- Lekki dataclass `AnalysisIndexEntry(role, origin, label, source, analysis, duration,
  sample_rate)` i `AnalysisIndex(version, sources)`.
- `load_analysis_index(recording_dir) -> AnalysisIndex | None`: czyta
  `analysis/index.json`; brak pliku → `None` (zgodność wstecz dla nagrań bez manifestu).
- Helpery wygody: `entries_by_role(role)`, `master()` (pierwszy/jedyny `master`),
  `stems()` oraz **`by_label(label)`** (selekcja po etykiecie — to deklarowany klucz
  rozróżniania, więc lookup jest częścią kontraktu, nie filtrowaniem po stronie konsumenta).
- **Rozwiązywanie ścieżek — ZDECYDOWANE (nie opcja):** pole przechowuje wartość względną,
  a wpis udostępnia metodę `resolved_analysis_path(recording_dir) -> Path` (i analogicznie
  dla `source`), składającą `recording_dir / value`. To jedyna droga, którą cymatic
  `--analysis-file` dostaje istniejącą, absolutną ścieżkę; bez tego R4 (DRY) nie jest
  spełnione (każdy konsument sklejałby ścieżkę sam).
- Walidacja: brak wymaganego pola / zły `version` → czytelny `ValueError` (fail-fast).

**Patterns to follow:** styl dataclass `RecordingStructure`; istniejące helpery
ścieżek w managerze.

**Test scenarios:**
- Happy path: poprawny `index.json` → `AnalysisIndex` z N wpisami; `master()` zwraca
  wpis `role: master`; `stems()` zwraca resztę.
- Happy path: `by_label("track_4_git")` zwraca właściwy wpis; nieznana etykieta → `None`.
- Happy path: `resolved_analysis_path(recording_dir)` zwraca **absolutną, istniejącą**
  ścieżkę (`recording_dir/analysis/<label>_analysis.json`) — gotową pod cymatic `--analysis-file`.
- Edge case: brak `index.json` → `None` (bez wyjątku).
- Edge case: `sources: []` → pusty `AnalysisIndex`, `master()` → `None`.
- Edge case: wpis bez `duration`/`sample_rate` (starszy manifest) — reader nie wybucha
  (pola opcjonalne/`None`), zgodność wprzód.
- Error path: brakujące pole wymagane/nieznany `version` → `ValueError`.
- Integration: round-trip — manifest zapisany przez `analyze-recording` (Unit 3) czyta
  się readerem bez utraty informacji (test na realnie wygenerowanym pliku).

**Verification:** Testy readera zielone; round-trip z Unit 3 spójny.

---

- [ ] **Unit 5: Dokumentacja — CLAUDE.md, wiki, kontrakt manifestu**

**Goal:** Workflow i kontrakt odkrywania są udokumentowane, by operator i przyszli
konsumenci wiedzieli, skąd biorą się analizy i jak je rozróżnić.

**Requirements:** R1, R3 (dokumentacyjnie)

**Dependencies:** Unit 1–4 (opis musi odpowiadać zachowaniu).

**Files:**
- Modify: `CLAUDE.md` (sekcja file-structure: zaznaczyć, że `bitwig/…/samples/` to
  źródło stemów fallback dla analizy; opis `analysis/index.json`).
- Modify: `~/dev/music-box-wiki` (workflow „Post-prod teledysk": „Analizuj" analizuje
  master + per-track z `bitwig/samples/`; sekcja Bitwig: capture vs Export Audio).
- (Opcjonalnie) Create: `docs/solutions/` wpis — gotcha „bitwig/samples = surowy capture
  niezależny od miksu; per-track triggery za darmo".

**Approach:**
- Krótko: drzewo struktury z adnotacją źródeł analizy; przykład `index.json` i jak
  konsument go czyta (`load_analysis_index`).
- Nie dokumentować per-strip targetingu jako gotowego — to wciąż przyszła robota.

**Test scenarios:** *(dokumentacja — brak testów automatycznych; weryfikacja przeglądem)*

**Verification:** Przegląd: opis zgodny z zachowaniem `analyze-recording`; przykład
`index.json` zgodny ze schematem z Unit 3/4.

## System-Wide Impact

- **Interaction graph:** „Analizuj" (fermata, **bez zmian**) → `beatrix analyze-recording`
  → `find_analysis_audio_sources` (tiery: mixed + stems|bitwig) → per-track
  `<clean>_analysis.json` + `analysis/index.json` → `status_detector.has_analysis_files`
  (dowolny `.json` → `Analyzed`, działa) → (przyszłość) cymatic/cinemon czytają manifest
  przez `load_analysis_index`.
- **Error propagation:** brak audio / kolizja → `ClickException` → stderr subprocessu →
  `Err(String)` w komendzie Tauri → `operationState.error` → render w `RecordingList`
  (ścieżka błędu naprawiona w poprzednim planie; tu bez zmian).
- **State lifecycle risks:** ponowne „Analizuj" przy zmienionym zestawie źródeł może
  zostawić **osierocone** `*_analysis.json`/nieaktualny `index.json` (stale). Manifest
  łagodzi (źródło prawdy o aktualnym zestawie), ale czyszczenie osieroconych plików
  odłożone (Deferred). Konsumenci powinni ufać `index.json`, nie globowi.
- **API surface parity:** nowe: `sanitize_stem_name`, `find_bitwig_sample_sources`,
  `load_analysis_index`, manifest `index.json`. Bez zmian: single-file `beatrix analyze`,
  sygnatury fermaty, kod cinemon/cymatic.
- **Integration coverage:** testy Python (CliRunner + tmp_path z atrapą `bitwig/samples/`,
  `mixed/`, `extracted/`) pokrywają tiery, sanityzację, manifest i round-trip readera.
  Realna analiza beatrix (librosa) niewymagana w testach CLI poza istniejącym wzorcem.

## Risks & Dependencies

- **`samples/` może zawierać nie-capture audio** (zaimportowane/biblioteczne sample) →
  zostaną zanalizowane jako „stem". MVP akceptuje; filtrowanie odłożone (Deferred).
  Ryzyko: nadmiarowe analizy + zaśmiecony manifest. Łagodzi: operator trzyma w projekcie
  tylko nagrane ścieżki.
- **Zmiana nazwy analiz (sanityzacja) vs dotychczasowa derywacja po stemie** — gdyby
  ktoś (lub stary skrypt) wyprowadzał nazwę analizy z surowej nazwy pliku, nie trafi.
  Dlatego manifest jest kontraktem; master (`master`) niezmieniony, więc istniejący
  master-aware cinemon działa dalej. **Konkretny footgun:** cinemon master-aware dopasowuje
  po stemie *dowolnego* `--main-audio` (`<stem>_analysis.json`), nie tylko `master.wav`.
  Dla nie-masterowego `main_audio` o nazwie ze znakami normalizowanymi przez `sanitize`
  (spacja/`+`/sufiks `-NN`) derywacja rozjedzie się z sanityzowaną nazwą analizy →
  cinemon cicho spadnie na `analysis_files[0]`. Mityguje: kontraktowa reguła „selekcja
  przez pole `analysis` z manifestu, nie przez derywację" (Key Decisions). Pełne
  podpięcie tej reguły w cinemon to przyszła faza konsumpcji (poza zakresem).
- **Stale pliki analiz** przy ponownym uruchomieniu — patrz State lifecycle.
- **Sekwencja:** Unit 2 zależy od Unit 1; Unit 3 od Unit 1+2; Unit 4 od kształtu z Unit 3;
  Unit 5 na końcu.
- **Test gotcha:** pytest po ścieżce (`uv run --package <pkg> pytest <path>`), nie pełne
  `uv run pytest`; `uv sync --all-packages`.

## Documentation / Operational Notes

- Po wdrożeniu: CLAUDE.md (file-structure + `index.json`) i `~/dev/music-box-wiki`
  (workflow „Post-prod teledysk", Bitwig capture vs Export Audio).
- Kandydat na wpis `docs/solutions/`: „bitwig/samples = surowy capture, per-track
  triggery animacji za darmo; mixed/ = polerowany Export Audio".

## Sources & References

- **Origin documents:**
  [docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md](docs/brainstorms/2026-06-04-bitwig-master-to-beatrix-requirements.md),
  [docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md](docs/brainstorms/2026-06-02-bitwig-mixed-audio-pipeline-requirements.md)
- Poprzednik (completed): `docs/plans/2026-06-04-001-feat-bitwig-master-to-beatrix-plan.md`
- Kod: `recording.py` (`find_analysis_audio_sources` l.364–413, `BITWIG_DIRNAME`),
  `beatrix/cli/click_cli.py` (`analyze-recording` l.124–171, `_analyze_single_file` l.60),
  `cinemon/config/cinemon_config_generator.py:186-201`, `cymatic/src/cymatic/cli.py`,
  `cymatic/src/cymatic/analysis_loader.py`
- Realne nagranie: `/home/wojtas/Wideo/obs/2026-06-04 15-15-01/` (`bitwig/samples/` z 6
  ścieżkami, `mixed/master.wav`, `analysis/master_analysis.json`)
