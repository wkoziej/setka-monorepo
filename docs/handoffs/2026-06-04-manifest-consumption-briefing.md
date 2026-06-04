<!-- ABOUTME: Handoff dla agenta wdrażającego konsumpcję manifestu analysis/index.json w cymatic/cinemon. -->
<!-- ABOUTME: Zbiera kontrakt odkrywania, API readera, punkty wejścia konsumentów i twarde reguły. -->

# Handoff: konsumpcja manifestu `analysis/index.json` w cymatic/cinemon

**Data:** 2026-06-04
**Cel:** Wpiąć w cymatic/cinemon odczyt manifestu `analysis/index.json` przez reader z
setka-common, tak by moduły **enumerowały i rozróżniały** analizy per-track (master vs
stem) zamiast globować po nazwie pliku.
**Status warstwy danych:** GOTOWA (PR #37, gałąź `feat/bitwig-per-track-analysis`).
Ten handoff dotyczy **fazy konsumpcji**, świadomie pozostawionej poza tamtym PR.

Wklej ten plik agentowi przez `#docs/handoffs/2026-06-04-manifest-consumption-briefing.md`.

---

## 1. Co już istnieje (warstwa danych — NIE zmieniaj)

Akcja „Analizuj" (fermata → `beatrix analyze-recording <dir>`) generuje:
- `analysis/<label>_analysis.json` dla **każdej** ścieżki nagrania:
  - master z `mixed/master.wav`,
  - stemy z `mixed/stems/` **lub** (fallback) z surowego capture `bitwig/<…>/samples/`,
  - ostateczny fallback `extracted/`.
- `analysis/index.json` — **manifest odkrywania** (kontrakt dla konsumentów).

Nazwy są **sanityzowane**: `track 4+git-24.wav` → `track_4_git_analysis.json`
(zdjęcie sufiksu Bitwiga `-NN`, normalizacja spacji/`+`/`/` → `_`).

## 2. Kontrakt manifestu `analysis/index.json`

Wszystkie ścieżki są **względne do katalogu nagrania**, z prefiksem katalogu.

```jsonc
{
  "version": 1,
  "sources": [
    { "role": "master", "origin": "mixed",  "label": "master",
      "source": "mixed/master.wav",
      "analysis": "analysis/master_analysis.json",
      "duration": 162.65, "sample_rate": 44100 },
    { "role": "stem",   "origin": "bitwig", "label": "track_4_git",
      "source": "bitwig/samples/track 4+git-24.wav",
      "analysis": "analysis/track_4_git_analysis.json",
      "duration": 162.65, "sample_rate": 44100 }
  ]
}
```

- `role` ∈ `master` | `stem` | `main` (`main` = fallback z `extracted/`).
- `origin` ∈ `mixed` | `bitwig` | `extracted`.
- `label` — czysta etykieta (sanityzowany stem).
- `source` / `analysis` — względne do `recording_dir`, z prefiksem katalogu.
- `duration` / `sample_rate` — opcjonalne (starszy manifest może ich nie mieć → `None`).

**Realny przykład do podejrzenia (7 wpisów):**
`/home/wojtas/Wideo/obs/2026-06-04 15-15-01/analysis/index.json`

## 3. API readera (to jest „z czego korzystasz")

Plik: `packages/common/src/setka_common/file_structure/specialized/analysis_index.py`
Testy jako żywe przykłady: `packages/common/tests/test_analysis_index.py`

```python
from setka_common import load_analysis_index, AnalysisIndex, AnalysisIndexEntry

idx = load_analysis_index(recording_dir)        # AnalysisIndex | None
# None, gdy brak manifestu → zgodność wstecz: zachowaj dotychczasową ścieżkę detekcji.

idx.version                                      # int
idx.sources                                      # list[AnalysisIndexEntry]
idx.master()                                     # AnalysisIndexEntry | None (role="master")
idx.stems()                                       # list[AnalysisIndexEntry] (role="stem")
idx.by_label("track_4_git")                      # AnalysisIndexEntry | None

entry.role, entry.origin, entry.label
entry.source, entry.analysis                      # wartości WZGLĘDNE (string)
entry.duration, entry.sample_rate                 # float|None, int|None
entry.resolved_analysis_path(recording_dir)       # -> Path absolutna do *_analysis.json
entry.resolved_source_path(recording_dir)         # -> Path absolutna do audio
```

Brak wymaganego pola lub nieznany `version` → `ValueError` (fail-fast).

## 4. Punkty wejścia konsumentów (co modyfikujesz)

- **cymatic**
  - `packages/cymatic/src/cymatic/cli.py` — flaga `--analysis-file PATH` (jawnie) lub detekcja.
  - `packages/cymatic/src/cymatic/analysis_loader.py` — `load_analysis(config)` czyta ścieżkę z konfiga; `VisualizerConfig.analysis_file`.
  - Pomysł integracji: gdy podano katalog nagrania zamiast pliku — `load_analysis_index` →
    domyślnie `master()`, z opcją wyboru per-`label` (np. nowa flaga `--stem <label>`),
    przekazując `resolved_analysis_path(recording_dir)` w miejsce `--analysis-file`.
- **cinemon**
  - `packages/cinemon/src/cinemon/config/cinemon_config_generator.py:186-201` — dziś
    master-aware (dobiera `<main_audio.stem>_analysis.json`).
  - Pomysł integracji: czytaj manifest i wybieraj wpis po `analysis` (patrz reguła R1 niżej).

## 5. Twarde reguły kontraktu (NIE łam)

- **R1 — selekcja przez pole `analysis`, nie przez derywację.** Nigdy nie wyprowadzaj
  nazwy analizy jako `<main_audio.stem>_analysis.json`. Sanityzacja rozjeżdża nazwę dla
  źródeł innych niż `master.wav` (np. surowy `track 4+git-24` → analiza `track_4_git_…`);
  derywacja trafiłaby w pustkę i cinemon **cicho** spadłby na `analysis_files[0]`.
  Master jest bezpieczny (`sanitize("master") == "master"`), więc istniejąca selekcja
  mastera działa — ale per-stem MUSI iść przez manifest.
- **R2 — `label` NIE jest stabilnym id** między uruchomieniami (zależy od nazwy pliku
  w Bitwigu). Nie buduj na nim trwałego mapowania strip↔stem. Trwałe wiązanie wymaga
  osobnego, stabilnego id — to przyszła robota (nie wymyślaj go teraz, YAGNI).
- **R3 — `duration`/`sample_rate` są w manifeście.** Użyj ich do walidacji zgodności
  master↔stem (różne SR/długości stemów z `bitwig/samples/`) bez otwierania N plików JSON.
- **R4 — brak manifestu (`None`) = zgodność wstecz.** Nagrania bez `index.json` muszą
  działać po staremu (dotychczasowa detekcja/`--analysis-file`).

## 6. Zakres i nie-cele

- **W zakresie:** odczyt manifestu w cymatic/cinemon + wybór właściwej analizy (master
  i/lub per-label).
- **Poza zakresem (na teraz):** pełny per-strip animation targeting (trwałe wiązanie
  konkretnego stemu audio z konkretnym stripem wideo) — wymaga stabilnego id (R2).
- **Bez zmian** w warstwie danych (beatrix `analyze-recording`, resolver, reader) i w
  fermacie.

## 7. Gotchas operacyjne

- **Testy uruchamiaj PO ŚCIEŻCE:** `uv run --package <pkg> pytest <path>` —
  gołe `uv run pytest` jest zepsute w monorepo. `uv sync --all-packages` przy brakach.
- Pre-commit odpala ruff (lint+format) i testy zmienionych pakietów — format potrafi
  przepisać plik i przerwać commit; wtedy `git add` przeformatowanego i commit ponownie.
- `bitwig/samples/*.wav` to **surowy capture** niezależny od miksu (efekty w Bitwigu są
  nieniszczące) — patrz `docs/solutions/2026-06-04-bitwig-samples-raw-capture-vs-mixed-export.md`.

## 8. Materiały źródłowe

- Plan warstwy danych: `docs/plans/2026-06-04-003-feat-bitwig-per-track-analysis-plan.md`
  (sekcje „High-Level Technical Design", „Key Technical Decisions", „Risks & Dependencies").
- PR: https://github.com/wkoziej/setka-monorepo/pull/37
- Reader + testy: `analysis_index.py`, `test_analysis_index.py` (ścieżki wyżej).
- Realny manifest: `/home/wojtas/Wideo/obs/2026-06-04 15-15-01/analysis/index.json`
