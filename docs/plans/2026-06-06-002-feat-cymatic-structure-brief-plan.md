---
title: "feat: Structure Brief audio dla autorowania klipu w cymatic"
type: feat
status: completed
date: 2026-06-06
origin: docs/brainstorms/2026-06-06-audio-structure-brief-for-cymatic-requirements.md
---

# feat: Structure Brief audio dla autorowania klipu w cymatic

## Overview

Nowe host-side narzędzie w cymatic, które czyta analizy beatrix nagrania
(`analysis/index.json` + per-stem `*_analysis.json`) i wyprowadza **zwięzły
structure brief** dla agenta-autora klipu (MCP): per-stem activity intervals
(„kto gra kiedy"), eventy ENTER/EXIT stemów, poziomy energii mastera + dropy.
Emituje trzy artefakty do `analysis/`: kanoniczny JSON, czytelny markdown i
heatmapę PNG (arrangement map). Celem jest zastąpienie „dłubania na żywo" mapą
audio, którą agent czyta raz i podejmuje świadome decyzje mapowania.

## Problem Frame

Bespoke looki cymatic autoruje agent LLM na żywo przez Blender MCP, bez mapy tego,
co audio robi w czasie. Jedyny sygnał struktury z beatrix
(`animation_events.sections`, agglomerative clustering chroma+MFCC, sztywne
`k=10`) jest słabym proxy — marnuje rozdzielczość na ciszę i scala korpus (dowód:
spike'i na nagraniach 22-37-24 i 15-15-01). Realna struktura aranżacji jest
czytelna z energii per stem. Odbiorcą priorytetowym jest **agent-autor (LLM)**,
co determinuje format: zwięzłe *wnioski* (brief), nie surowe tablice i nie sam
obraz. (see origin: docs/brainstorms/2026-06-06-audio-structure-brief-for-cymatic-requirements.md)

## Requirements Trace

- R1. Czyta `analysis/index.json` + per-stem `*_analysis.json` przez
  `setka_common.load_analysis_index`; bez stemów degraduje się do briefu z samego
  mastera (degradacja, nie błąd).
- R2. Per-stem activity intervals z wygładzonej, p99-znormalizowanej obwiedni
  energii broadband (bass+mid+high); scala krótkie luki; oznacza stemy ≈ciche.
- R3. Eventy ENTER/EXIT stemów wyprowadzone z R2.
- R4. Energia mastera zredukowana do poziomów (low/mid/high) + wykrycie dropów.
- R5. Output 1 — structure brief: kanoniczny JSON + czytelny markdown; dokładne
  czasy (~1 s), semantyka, mały rozmiar (setki–niskie tysiące tokenów).
- R6. Output 2 — PNG-podgląd: arrangement heatmap (stem × czas × energia) + panel
  energii mastera.
- R7. Artefakty zapisywane w `analysis/`, odkrywalne obok analiz.
- R8. Brief jawnie deklaruje podział oparty o aktywność/energię, NIE o
  `beatrix.sections`.

## Scope Boundaries

- Bez energy/novelty-based segmentacji na sekcje (osobny przyszły etap).
- Bez wpięcia kanałów `gate_<stem>` do `data_object`.
- Bez naprawy `beatrix.sections`, bez integracji z fermatą/GUI.
- Bez automatycznego sterowania sceną — brief tylko informuje agenta.

## Context & Research

### Relevant Code and Patterns

- `packages/cymatic/src/cymatic/cli.py` — wzorzec CLI: **argparse**,
  `def main(argv=None) -> int`. Entry point w `pyproject.toml`:
  `[project.scripts] cymatic-render = "cymatic.cli:main"`. Nowe narzędzie mirroruje
  ten kształt.
- `packages/cymatic/src/cymatic/normalization.py` — `normalize_band(arr) -> np.ndarray`
  (p99-anchor do [0,1], odporny na transienty). **Reużywany** do normalizacji
  broadband energy — nie duplikować logiki p99.
- `packages/cymatic/src/cymatic/config.py` — wzorzec dataclass + JSON
  serialization (`.to_json()/.from_json()`). Brief dataclassy mirrorują ten styl.
- `setka_common` (`packages/common/.../file_structure/specialized/analysis_index.py`)
  — `load_analysis_index(recording_dir) -> AnalysisIndex | None`; `AnalysisIndex`
  ma `.master()`, `.stems()`, `.by_label()`; `AnalysisIndexEntry` ma
  `role/origin/label/source/analysis/duration/sample_rate` +
  `.resolved_analysis_path(recording_dir)`.
- `RecordingStructureManager` — `ANALYSIS_DIRNAME = "analysis"`,
  `ensure_analysis_dir(recording_dir)` do tworzenia/wskazania katalogu artefaktów.
- `packages/cymatic/tests/` — `conftest.py` z fixturami; markery `unit`/
  `integration`/`slow`; `--cov-fail-under=80`; testy host-side jako klasy
  `TestXxx`, fixtures JSON pod `tests/` (skip gdy brak). Wzorzec: `test_normalization.py`,
  `test_analysis_loader.py`.
- Surowy format analizy (beatrix): `frequency_bands.{times,bass_energy,mid_energy,high_energy}`,
  `tempo.bpm`, `duration` — patrz `packages/beatrix/src/beatrix/core/audio_analyzer.py`.

### Institutional Learnings

- Spike walidacyjny (ten brainstorm) dowiódł: naiwny active-set scala sustain
  (gitara → 106 s jeden blok) i rozsypuje się na perkusji (m:s migocze jako
  uderzenia). Stąd MVP daje **activity intervals per stem**, a NIE pochodne
  sekcje — segmentacja odłożona.
- p99-normalizacja per stem jest konieczna, by ciche stemy były widoczne niezależnie
  od głośności (zgodnie z `normalize_band`).

### External References

- Nie zbierano — numpy/matplotlib to znane technologie, repo ma mocne lokalne
  wzorce host-side (analysis_loader, normalization). External research pominięty.

## Key Technical Decisions

- **Lokalizacja: cymatic host-side** (`packages/cymatic/src/cymatic/brief.py`), nie
  beatrix. Uzasadnienie: to narzędzie *dla* autorowania cymatic, host-side ma już
  numpy i wzorce (normalization, cli), a beatrix pozostaje czystym producentem
  analiz. (rozstrzyga deferred z origin)
- **Wczytanie: surowy JSON `frequency_bands`, nie `load_analysis`.** `load_analysis`
  wymaga pełnego `VisualizerConfig` i liczy `beat_env/peak_env` (zbędne dla MVP).
  Brief czyta tylko `frequency_bands`, `tempo.bpm`, `duration` z JSON i reużywa
  `normalize_band` dla broadband. Mniej sprzężenia, ten sam algorytm p99.
- **Broadband energy = bass+mid+high (suma), potem `normalize_band`.** Próg
  aktywności stosowany na wygładzonej, znormalizowanej krzywej.
- **Parametry detekcji jako nazwane stałe z domyślnymi** (z walidacji: smoothing
  ~1 s, próg ~0.10 po p99, scalanie luk ~2 s, min-segment ~2.5 s). Strojenie
  odłożone do implementacji/użycia.
- **matplotlib jako twarda zależność cymatic** (FAIL FAST — brak fallbacku bez
  zgody). Render przez backend `Agg` (headless).
- **Artefakty w `analysis/`**: `structure_brief.json`, `structure_brief.md`,
  `structure_map.png`. Spójne z odkrywalnością obok `index.json` (R7); heatmapa to
  artefakt analityczny, nie render wideo — stąd `analysis/`, nie `blender/render/`.
- **Markdown to render z kanonicznego JSON**, nie osobne źródło prawdy — jeden
  model danych, dwie reprezentacje.

## Open Questions

### Resolved During Planning

- Gdzie umieścić narzędzie? → cymatic host-side (patrz Key Technical Decisions).
- Czy używać `load_analysis`? → Nie; surowy JSON + `normalize_band` (MVP nie
  potrzebuje envelope).
- matplotlib opcjonalny czy twardy? → Twarda zależność cymatic.
- Schemat JSON briefu? → Zdefiniowany w High-Level Technical Design.
- Lokalizacja artefaktów? → `analysis/` (trzy pliki).

### Deferred to Implementation

- Dokładne wartości progów/okien detekcji activity i dropu — strojenie na kilku
  realnych nagraniach po zobaczeniu wyników; domyślne z walidacji jako start.
- Odróżnienie stemów perkusyjnych (fragmentaryczne interwały) od sustain — możliwa
  adnotacja typu/„fragmentation", ale dopiero gdy domyślny gate okaże się
  niewystarczający. Nie blokuje MVP.
- Czy i jak dołączać `beatrix.sections` jako opcjonalne tło w PNG — domyślnie
  pominięte; decyzja po obejrzeniu pierwszych heatmap.

## High-Level Technical Design

> *Ilustruje zamierzone podejście — directional guidance do review, nie specyfikacja
> implementacji. Implementujący traktuje to jako kontekst, nie kod do odtworzenia.*

Przepływ danych:

```
load_analysis_index(recording_dir)
        │  master entry + stems[]
        ▼
for each entry: read JSON → frequency_bands (times, bass, mid, high)
        │
        ├─ broadband = bass+mid+high ─► normalize_band ─► smooth ─► gate(>próg)
        │        └─► activity intervals (merge luk, min-segment)  [R2]
        │                 └─► ENTER/EXIT events                    [R3]
        │
        └─ master broadband ─► poziomy low/mid/high + detekcja dropów  [R4]
        ▼
StructureBrief (dataclass)
        ├─ to_dict()/to_json()  ─► analysis/structure_brief.json   [R5]
        ├─ render_markdown()    ─► analysis/structure_brief.md      [R5]
        └─ render_heatmap()     ─► analysis/structure_map.png       [R6]
```

Szkic kształtu kanonicznego JSON (pola directional, nie ostateczne nazwy):

```
{
  "recording": "<dir name>", "duration": 162.7, "bpm": 89,
  "segmentation": "energy/activity-based (NOT beatrix.sections)",   # R8
  "stems": [
    {"label": "track_1", "active": [[54.0,151.2]], "silent": false},
    {"label": "track_3", "active": [], "silent": true}
  ],
  "events": [{"t": 54.0, "kind": "enter", "stem": "track_1"}, ...],
  "master_energy": {"levels": [{"start":0,"end":7,"level":"low"}, ...],
                    "drops": [58.2]}
}
```

## Implementation Units

- [ ] **Unit 1: Rdzeń — wczytanie analiz + per-stem activity + energia/eventy**

**Goal:** Czysta-numpy logika: z `analysis/index.json` policzyć per-stem activity
intervals, eventy ENTER/EXIT, poziomy energii mastera i dropy. Bez I/O artefaktów,
bez CLI — w pełni testowalne jednostkowo.

**Requirements:** R1, R2, R3, R4

**Dependencies:** Brak

**Files:**
- Create: `packages/cymatic/src/cymatic/brief.py`
- Modify: `packages/cymatic/src/cymatic/__init__.py` (eksport publicznych symboli, jeśli zgodne z konwencją pakietu)
- Test: `packages/cymatic/tests/test_brief.py`

**Approach:**
- `load_analysis_index(recording_dir)`; gdy `None` → czytelny błąd (brak manifestu).
- Dla każdego entry (`master` + `stems()`): wczytać surowy JSON spod
  `entry.resolved_analysis_path(recording_dir)`, wyciągnąć `frequency_bands`.
- `broadband = bass+mid+high`; `normalize_band(broadband)` (reużycie z
  `normalization.py`); wygładzić oknem ~1 s liczonym z `times` (krok = `times[1]-times[0]`).
- Activity: próg na wygładzonej krzywej → runy; scalić luki < ~2 s; odrzucić
  segmenty < ~2.5 s; stem z sumaryczną aktywnością < ~5 s → `silent=True`.
- ENTER/EXIT: krawędzie interwałów activity per stem.
- Master: te same kroki → średnia energia w oknach → kubełki low/mid/high; drop =
  wzrost energii o > próg między sąsiednimi oknami (po spadku/ciszy).
- Parametry jako moduł-poziom stałe (`SMOOTH_S`, `ACTIVITY_THRESH`, `GAP_MERGE_S`,
  `MIN_SEGMENT_S`, `SILENT_MAX_S`, `DROP_DELTA`).
- Dataclassy: `StemActivity(label, active: list[tuple], silent: bool)`,
  `StructureBrief(recording, duration, bpm, stems, events, master_levels, drops)`.

**Execution note:** Implementować test-first — logikę detekcji łatwo zweryfikować
na syntetycznych obwiedniach o znanych wejściach.

**Patterns to follow:**
- `normalize_band` z `normalization.py` (nie duplikować p99).
- Dataclass + przyszłe `to_dict` w stylu `config.py`.
- Iteracja `index.master()` / `index.stems()` + `resolved_analysis_path`.

**Test scenarios:**
- Happy path: syntetyczny stem z energią wysoką w [10,20] s, zerową poza →
  `active == [(10,20)]`, `silent == False`.
- Happy path: dwa stemy o rozłącznych oknach → poprawne interwały + ENTER/EXIT na
  krawędziach.
- Edge case: stem o energii ~0 przez cały czas → `silent == True`, `active == []`.
- Edge case: dwa krótkie aktywne fragmenty oddzielone luką < `GAP_MERGE_S` →
  scalone w jeden interwał; luka > `GAP_MERGE_S` → osobne.
- Edge case: aktywny fragment krótszy niż `MIN_SEGMENT_S` → odrzucony.
- Edge case: stemy o różnym `sample_rate`/długości `times` → każdy liczony na swojej
  osi czasu, brak błędu wyrównania.
- Error path: brak `index.json` (`load_analysis_index` → `None`) → czytelny wyjątek/błąd.
- R4: master z wyraźnym skokiem energii po ciszy → drop wykryty blisko (~1 s) granicy;
  poziomy low/mid/high przypisane wg energii.
- R1 degradacja: index bez stemów (sam master) → brief z pustą listą stemów, sekcja
  master_energy obecna, brak wyjątku.

**Verification:**
- Detekcja na syntetycznych danych zwraca interwały zgodne z wejściem w granicach
  tolerancji kroku czasu; `silent`/ENTER/EXIT/drops poprawne; pokrycie testami
  utrzymuje próg pakietu (≥80%).

- [ ] **Unit 2: Serializacja briefu — JSON + markdown**

**Goal:** Zamienić `StructureBrief` na kanoniczny JSON i czytelny markdown
zaprojektowany pod konsumpcję przez agenta (dokładne czasy, semantyka, zwięzłość).

**Requirements:** R5, R8

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/cymatic/src/cymatic/brief.py`
- Test: `packages/cymatic/tests/test_brief.py`

**Approach:**
- `StructureBrief.to_dict()/to_json()` w stylu `config.py`; pola wg szkicu JSON
  (High-Level Technical Design), w tym `segmentation` jawnie deklarujące źródło
  podziału (R8).
- `render_markdown(brief) -> str`: sekcje „Sections/activity", „Per-stem activity",
  „Events", „Master energy" — z dokładnymi czasami i oznaczeniem ≈silent (`skip
  mapping`). Format zwięzły (cel: setki–niskie tysiące tokenów).

**Patterns to follow:**
- JSON serialization z `config.py` (`.to_json()`).

**Test scenarios:**
- Happy path: round-trip `to_dict` → wszystkie pola obecne, typy serializowalne
  (brak `np.float64` w wyjściu — rzutowanie na `float`).
- R8: JSON i markdown zawierają jawną deklarację „NOT beatrix.sections".
- Happy path: markdown listuje każdy stem z interwałami; stem `silent` oznaczony
  jako do pominięcia.
- Edge case: brief bez stemów (degradacja) → markdown sensowny, bez pustych/błędnych
  sekcji.
- Rozmiar: markdown dla typowego nagrania (≤8 stemów) mieści się w zwięzłym budżecie
  (np. < ~6 KB) — asercja sanity na długość.

**Verification:**
- JSON deserializuje się z powrotem do równoważnej struktury; markdown czytelny,
  zawiera wszystkie stemy/eventy/dropy i deklarację źródła podziału.

- [ ] **Unit 3: Heatmapa PNG (arrangement map)**

**Goal:** Render PNG: heatmapa stem × czas × energia + panel energii mastera, jako
gestalt dla człowieka i agenta multimodalnego.

**Requirements:** R6

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/cymatic/src/cymatic/brief.py`
- Modify: `packages/cymatic/pyproject.toml` (dodać `matplotlib` do `dependencies`)
- Test: `packages/cymatic/tests/test_brief.py`

**Approach:**
- `render_heatmap(brief_inputs, output_png)`; matplotlib z backendem `Agg`.
- Resampling obwiedni każdego stemu na wspólną siatkę czasu (np. `np.interp`) →
  macierz do `imshow` (origin upper, extent po czasie), etykiety = labele stemów.
- Dolny panel: energia mastera + znaczniki dropów; wspólna oś X.
- Render musi działać headless (bez DISPLAY) — `matplotlib.use("Agg")` przed
  `pyplot`.

**Patterns to follow:**
- Wzorzec ze spike'a `/tmp/cymatic_spike_stems.py` (heatmapa `imshow` + panel
  master) — jako referencja kompozycji, nie kod do skopiowania.

**Test scenarios:**
- Happy path (smoke): dla briefu z 2–3 stemami `render_heatmap` tworzy niepusty plik
  PNG i nie rzuca.
- Edge case: brief bez stemów → render nie wywala się (sam panel master albo czytelny
  komunikat na obrazie).
- Integration: backend `Agg` aktywny — render działa bez DISPLAY (środowisko CI).

**Verification:**
- PNG powstaje, ma rozmiar > 0; brak wyjątków przy braku stemów; działa headless.

- [ ] **Unit 4: CLI + entry point + zapis artefaktów**

**Goal:** Spiąć całość w komendę `cymatic-structure-brief`, która z katalogu
nagrania generuje i zapisuje trzy artefakty do `analysis/`.

**Requirements:** R1, R5, R6, R7

**Dependencies:** Unit 1, Unit 2, Unit 3

**Files:**
- Modify: `packages/cymatic/src/cymatic/brief.py` (`def main(argv=None) -> int`)
- Modify: `packages/cymatic/pyproject.toml` (`[project.scripts]
  cymatic-structure-brief = "cymatic.brief:main"`)
- Test: `packages/cymatic/tests/test_brief.py`

**Approach:**
- argparse wg wzorca `cli.py`: pozycyjny `recording_dir`; opcjonalne
  `--output-brief`, `--output-markdown`, `--output-heatmap` (domyślne w `analysis/`).
- `RecordingStructureManager.ensure_analysis_dir(recording_dir)` przed zapisem.
- Zapis: `structure_brief.json`, `structure_brief.md`, `structure_map.png`;
  wypisać ścieżki na stdout; zwrócić 0.
- Błędy (brak manifestu/katalogu) → czytelny komunikat i kod ≠ 0 (FAIL FAST).

**Patterns to follow:**
- `cli.py` `main(argv=None) -> int`; rejestracja entry pointa w `[project.scripts]`.

**Test scenarios:**
- Happy path: tymczasowy `recording_dir` (tmp_path) z `index.json` + 2 mini
  `*_analysis.json` → `main([dir])` zwraca 0, tworzy trzy pliki w `analysis/`.
- R7: artefakty lądują w `analysis/`, ścieżki wypisane na stdout.
- R1 degradacja: index bez stemów → komenda kończy się 0, brief/markdown/PNG powstają.
- Error path: katalog bez `analysis/index.json` → kod ≠ 0 i czytelny komunikat.
- Override: `--output-*` kieruje artefakty pod wskazane ścieżki.

**Verification:**
- `uv run --package cymatic cymatic-structure-brief <dir>` (lub wywołanie `main`)
  generuje trzy odkrywalne artefakty; ścieżki na stdout; kod 0 przy poprawnym
  nagraniu, ≠0 przy braku manifestu.

## System-Wide Impact

- **Interaction graph:** Nowy, izolowany entry point host-side. Nie modyfikuje
  ścieżki `cymatic-render` ani in-Blender. Konsumuje wyłącznie istniejące artefakty
  beatrix (read-only).
- **Error propagation:** Brak `index.json`/`frequency_bands` → jawny błąd z kodem ≠0,
  bez cichych fallbacków.
- **State lifecycle risks:** Zapis trzech plików do `analysis/`; nadpisanie
  istniejących artefaktów briefu jest akceptowalne (idempotentne). Nie dotyka
  `*_analysis.json` ani `index.json`.
- **API surface parity:** Nowa zależność `matplotlib` wchodzi do cymatic — wymaga
  `uv sync`/`uv lock`. Brak wpływu na inne pakiety.
- **Integration coverage:** Test end-to-end na syntetycznym `recording_dir`
  (Unit 4) pokrywa łańcuch index → brief → trzy artefakty, czego testy czystej
  logiki (Unit 1) nie udowadniają.

## Risks & Dependencies

- **matplotlib jako nowa zależność** — zwiększa wagę instalacji cymatic. Akceptowane
  świadomie (PNG to wymaganie R6). Mitygacja: `Agg`, brak importu na ścieżce
  `cymatic-render`.
- **Jakość parametrów detekcji** — domyślne z walidacji mogą wymagać strojenia na
  innym materiale (perkusja vs sustain). Mitygacja: parametry jako nazwane stałe,
  strojenie jawnie deferred; MVP i tak daje activity bardziej użyteczne niż `sections`.
- **Zależność od wcześniejszego `beatrix analyze-recording`** — bez analiz brief nie
  ma wejścia (oczekiwane; jasny błąd).

## Documentation / Operational Notes

- Dodać `cymatic-structure-brief` do listy CLI entry points w
  `packages/cymatic` (README/CLAUDE.md) i ewentualnie w głównym `CLAUDE.md`
  (sekcja CLI Entry Points) — po implementacji.
- `uv lock` po dodaniu matplotlib.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-06-audio-structure-brief-for-cymatic-requirements.md](docs/brainstorms/2026-06-06-audio-structure-brief-for-cymatic-requirements.md)
- Related code: `packages/cymatic/src/cymatic/{cli,normalization,config,analysis_loader}.py`,
  `packages/common/.../file_structure/specialized/analysis_index.py`,
  `packages/beatrix/src/beatrix/core/audio_analyzer.py`
- Walidacja: spike'i `/tmp/cymatic_spike_*.py` (jednorazówki, nie w repo)
