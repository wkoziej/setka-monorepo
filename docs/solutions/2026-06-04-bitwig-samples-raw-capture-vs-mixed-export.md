---
title: "bitwig/samples/ = surowy capture niezależny od miksu — per-track triggery animacji za darmo"
date: 2026-06-04
tags: [bitwig, audio, analysis, beatrix, per-track, stems, pipeline, setka-common]
component: audio-analysis
status: resolved
related_plans:
  - docs/plans/2026-06-04-003-feat-bitwig-per-track-analysis-plan.md
---

# bitwig/samples/ — surowy capture vs mixed/ — przetworzony eksport

## Symptom / kontekst

Pipeline Setka ma dwa miejsca z plikami audio per-instrument:
- `bitwig/samples/` — pliki pojawiające się automatycznie po nagraniu multitrack w Bitwigu
- `mixed/stems/` — pliki eksportowane ręcznie przez `File → Export Audio`

Pytanie: które z nich nadają się do analizy audio w Beatrixie? Czy muszę eksportować stemy, żeby dostać per-track analizę?

## Przyczyna (rdzeń)

**Efekty, EQ i głośności ścieżek w Bitwigu są niededestrukcyjne** — zapisane w `.bwproject`, nie w plikach audio. Pliki w `bitwig/samples/` to zawsze **surowy capture** z chwili nagrywania. Przetworzony (z efektami, EQ, głośnością) dźwięk istnieje tylko w pamięci podczas odtwarzania projektu lub po jawnym Bounce/Export Audio.

Konsekwencja: `bitwig/samples/*.wav` to czyste surowe przebiegi per-instrument — i właśnie to jest wystarczające do wykrywania bitów, energii i segmentów per-track (Beatrix potrzebuje charakteru rytmicznego ścieżki, nie jej finalnej brzmienia).

## Hierarchia źródeł w beatrix analyze-recording

```
1. mixed/master.wav      → role=master, origin=mixed  (finalny mix z efektami)
2. mixed/stems/*.wav     → role=stem,   origin=mixed  (przetworzone stemy)
3. bitwig/samples/*.wav  → role=stem,   origin=bitwig (surowy capture — fallback)
4. extracted/*.wav       → role=main,   origin=extracted (audio z OBS — ostatni fallback)
```

`beatrix analyze-recording <dir>` przechodzi przez tę hierarchię automatycznie i zapisuje `analysis/index.json` (manifest) + `analysis/<track>_analysis.json` per ścieżka.

## Rozwiązanie

Nie trzeba eksportować stemów żeby dostać per-track analizę. `bitwig/samples/` wystarczą jako fallback. Jeśli zależy ci na dokładności (np. po wyciszeniu basu w projekcie — nie chcesz żeby basy triggerowały animacje), wyeksportuj stemy do `mixed/stems/` — wtedy to one mają pierwszeństwo.

## Reguły operacyjne

- **Nie czyść `bitwig/samples/`** po nagraniu — to źródło per-track analizy dopóki nie masz stemów
- **Export stemów = lepsza jakość analizy** (z efektami) ale nie jest obowiązkowy
- **`analysis/index.json`** to kontrakt odkrywania — czytaj przez `load_analysis_index()` z setka-common, nie skanuj `analysis/` ręcznie
- Nazwy plików w `samples/` są sanityzowane przy tworzeniu wpisów index (`track 4+git-24.wav` → `track_4_git_analysis.json`)

## Weryfikacja

```bash
beatrix analyze-recording "/path/to/recording"
cat "/path/to/recording/analysis/index.json"
# Powinno zawierać wpisy z origin="bitwig" gdy brak mixed/stems/
```

## Powiązania

- [Plan 003 — per-track analysis](../plans/2026-06-04-003-feat-bitwig-per-track-analysis-plan.md)
