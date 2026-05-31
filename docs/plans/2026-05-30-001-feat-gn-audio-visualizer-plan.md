---
title: "feat: Wizualizer audio 3D (Geometry Nodes + Blender MCP)"
type: feat
status: active
date: 2026-05-30
origin: docs/brainstorms/2026-05-30-gn-audio-visualizer-requirements.md
---

# feat: Wizualizer audio 3D (Geometry Nodes + Blender MCP)

## Overview

Nowy pakiet workspace (`cymatic`, nazwa robocza) generuje **abstrakcyjny wizualizer 3D** sterowany analizą `beatrix`, renderowany do mp4. Cała piosenka jest kodowana jako jeden obiekt-danych w scenie (mesh: X = czas, atrybuty wierzchołków = znormalizowane `bass/mid/high` + prekomputowane obwiednie beatów/peaków). Drzewo Geometry Nodes **próbkuje** ten obiekt po bieżącym czasie sceny i czyta wszystkie cechy naraz (most „mesh-jako-dane", podejście B). Look sceny budowany iteracyjnie z pomocą **Blender MCP** (statyczny screenshot = kompozycja), ale **synchronizacja jest weryfikowana z danych, nie z obrazu** — to ograniczenie MCP odkryte w researchu (brak ruchu/klipu w screenshocie).

Źródłem prawdy renderu jest **skrypt-builder GN (Python) + dataclass parametrów presetu**, commitowane do repo; `.blend` z pętli MCP = produkt uboczny. `beatrix` pozostaje nietknięty (single source).

**Dostawa fazowa:** Faza A de-ryzykuje trzema spike'ami z bramkami kill/continue **przed** pełnym buildem. Faza B to MVP build. Faza C (poza gate MVP) to autonomiczna pętla MCP.

## Docelowy workflow (UX — potwierdzony empirycznie 2026-05-31)

```
1. AUDIO        twórca wskazuje utwór (dowolny format librosa: wav/flac/mp3...)
      │
2. ANALIZA      beatrix analyze --beat-division 1  →  *_analysis.json
      │         (single source of truth; beat_division=1 dla gęstych beatów)
      │
3. PRZYGOTOWANIE  cymatic host-side: normalizacja per-track p99 + prekomputacja
      │           obwiedni beat/peak + dt z times[]  →  dane gotowe do GN
      │
4. PROPOZYCJA   Claude (przez Blender Lab MCP / socket) buduje scenę GN w żywym
      │           Blenderze: data-object + sampler (most B) + preset wizualny.
      │           Screenshot/short-render → Claude ocenia kompozycję, poprawia
      │           (pętla autoringu, ≤K iteracji). Sync = z danych, nie z obrazu.
      │
5. AKCEPTACJA   twórca ogląda (Play w viewport / klip) → akceptuje look (R4).
      │           Zaakceptowany look „freeze" → builder.py + PresetParams (commit).
      │
6. RENDER       headless, osobno (nie MCP): builder + params + analysis → mp4
                w blender/render/. (Render wideo: patrz uwaga niżej.)
```

**Potwierdzone w tej sesji (Spike 0/1/2/3a):** kroki 1-5 zadziałały end-to-end na żywej maszynie — Claude napędził Blender 5.1.2 przez socket MCP, zbudował reaktywną scenę z realnej analizy, sync potwierdzony.

**⚠ Uwaga render (krok 6):** ten build Blendera 5.1.2 jest **bez wewnętrznego enkodera FFMPEG** i brak systemowego `ffmpeg`. Render do mp4 wymaga instalacji `ffmpeg` (i tak wymagany w CLAUDE.md) → render klatek PNG + mux. Podgląd/akceptacja (krok 5) działa bez tego (Play w Blenderze z sound strip).

## Problem Frame

Dane `beatrix` (beaty, onsety, energy_peaks, time-series energii pasm) są dziś konsumowane wyłącznie przez `cinemon` w trybie VSE — animacje 2D na paskach. Brak ścieżki generującej proceduralną wizualizację **3D** z tej samej analizy. Cel: nowy typ outputu z istniejącego pipeline'u (OBS → beatrix → render), autoring sceny przez agenta zamiast ręcznej pracy node-by-node nad driverami. (see origin: `docs/brainstorms/2026-05-30-gn-audio-visualizer-requirements.md`)

## Requirements Trace

- **R1** — Z istniejącego `*_analysis.json` powstaje scena 3D reagująca na: (a) ciągłą **znormalizowaną** energię pasm i (b) dyskretne beaty/peaki (origin: kryterium MVP 1).
- **R2** — Sync **obiektywny (timing danych)**: akcenty wizualne padają w granicach **±N klatek** (N np. ≤2) od timestampów beatrix — mierzalne z danych (arytmetyka `Seconds/dt`). **Decyzja:** percepcyjne „akcent widać na beacie" NIE jest dowodzone tu (obwiednia prekomputowana → harness dowodzi indeksu, nie pikseli) — pokrywa je **akceptacja twórcy (R4)**. Kryterium MVP 2 = dowód timingu danych, świadomie nie wizualnego (origin: kryterium MVP 2; review: adversarial-tautologia).
- **R3** — Próbkowanie po czasie poprawne dla dowolnej klatki, **mierzone na ≥2 utworach o RÓŻNYM `sample_rate`** (origin: kryterium MVP 3).
- **R4** — **Stop-rule (binarny, MVP):** twórca akceptuje **≥1 wyrenderowany klip** jako warty użycia; brak akceptacji → fail gate + fallback generuj-raz. **Bez licznika ≤K w MVP** — budżet iteracji należy wyłącznie do R5 (decyzja: K tylko dla autonomicznej pętli) (origin: kryterium MVP 4).
- **R5** *(Faza 2, poza gate MVP)* — Pętla MCP autoringu zbiega bez ręcznej ingerencji w node'y w **budżecie ≤K iteracji** (K np. 5) (origin: kryterium Fazy 2 — 5).
- **INV1** *(inwariant architektoniczny)* — `beatrix` jest jedynym źródłem analizy; nowy moduł nie liczy własnej analizy audio (origin: Decyzja 4).
- **INV2** *(inwariant)* — Determinizm: `builder + preset-params + analysis.json` → ten sam render; `.blend` nieistotny dla reprodukcji (origin: Otwarte 5).

## Scope Boundaries

- **Brak** łączenia warstwy 3D z footage OBS (osobny, późniejszy pomysł).
- **Brak** własnej analizy audio — wszystkie dane z `beatrix` (INV1).
- **Brak** renderu produkcyjnego przez MCP — render leci osobno, headless.
- **Brak** biblioteki wielu presetów na start — MVP = jeden dobry preset hybrydowy.
- **Brak** real-time playera dla widza. Podgląd przez screenshoty MCP **jest** w zakresie.
- **`animation_events.sections` POMINIĘTE na MVP** — to listy dictów `{start,end,label}`, nie skalary; hybryda i R1 ich nie wymagają.
- **System YAML `cinemon` NIE jest reużywany** — config MVP = prosty dataclass (origin: Decyzja zakresu; jeden preset).

### Deferred to Separate Tasks

- Normalizacja porównywalna **między utworami** (skala absolutna/log): późniejsze rozszerzenie poza MVP (per-track i cross-track są sprzeczne — origin: Decyzja 5).
- Migracja config dataclass → wzorzec YAML `cinemon`: dopiero gdy pojawi się drugi preset (origin: Otwarte 4).
- Kodowanie `sections` jako danych dla przejść scen: po MVP.

## Context & Research

### Relevant Code and Patterns

- **Subprocess Blendera:** `packages/cinemon/src/cinemon/project_manager.py` — `BlenderProjectManager` buduje `[blender, "--background", "--python", <script>, "--", "--config", <path>]`, `subprocess.run(..., capture_output=True, text=True, check=True)`, `RuntimeError` na `CalledProcessError`. **UWAGA: domyślna gałąź `snap run blender` jest Linux-only** — na macOS wymaga jawnego `blender_executable`.
- **Parsowanie `--config` w Blenderze:** `packages/cinemon/blender_addon/vse_script.py` skanuje `sys.argv` po `--config`.
- **Struktura katalogów:** `packages/common/src/setka_common/file_structure/specialized/recording.py` — `ensure_blender_dir()` tworzy `blender/` + `blender/render/`; `get_analysis_file_path()` → `analysis/{stem}_analysis.json`. Wszystkie `@staticmethod`. **Nie hardkodować nazw katalogów.**
- **Wybór audio:** `packages/beatrix/src/beatrix/core/audio_validator.py` — `AudioValidator.detect_main_audio(extracted_dir, specified_audio=None)`, bezstanowy, komunikaty błędów po polsku.
- **Kontrakt danych beatrix:** `packages/beatrix/src/beatrix/core/audio_analyzer.py` — `analyze_for_animation()` zwraca `duration`, `sample_rate` (z `librosa.load(sr=None)` → natywny sr), `tempo.{bpm,beat_times,beat_count}`, `animation_events.{beats,onsets,energy_peaks,sections}`, `frequency_bands.{times,bass_energy,mid_energy,high_energy}`. Pasma = `np.mean(np.abs(stft), axis=0)` — **surowe nieznormalizowane magnitudy**. `times = frames_to_time(arange(...), sr=sr)` z `hop_length=512` → **krok siatki `hop_length/sr` zależny od utworu**.
- **Testy bez Blendera:** `packages/cinemon/tests/conftest.py` — `autouse` fixture `mock_bpy` wstrzykuje `Mock` do `sys.modules["bpy"]`; `mock_subprocess` patchuje `subprocess.run`. Moduły in-Blender używają `try: import bpy / except ImportError: bpy = None`.

### Institutional Learnings

- **Brak `docs/solutions/`** — to pierwszy artefakt wiedzy w tym obszarze. Rozważyć `/ce:compound` po spike'ach (GN time-sampling, normalizacja, pętla MCP).
- **`docs/DATA_FLOW_SPECIFICATION.md` ma NIEAKTUALNY schemat JSON** (pokazuje zagnieżdżone `spectral_analysis.frequency_bands.bass.energy`). **Ufać kodowi `audio_analyzer.py` i brainstormowi**, nie temu spec — reużyć z niego tylko konwencję katalogów `blender/render/`.

### External References

- **Blender MCP** (`ahujasid/blender-mcp`, v1.5.6, 2026-03): eksponuje `execute_blender_code` (dowolny `bpy`) i `get_viewport_screenshot` (zwraca obraz jako MCP `Image`, ~800px). **Brak dedykowanego narzędzia GN** (PR #92 niezmergowany). **Brak ruchu/klipu/playbacku** — screenshot to statyczna klatka → **sync nieweryfikowalny z obrazu**. Alternatywy: oficjalny Blender Lab MCP (early, first-party), lub **własny cienki socket-bridge / headless `bpy`** (może mniej pracy niż cudzy addon, sandbox pod kontrolą). `execute_blender_code` = niesandboxowany kod LLM → throwaway plik.
- **GN time-sampling** (Blender 4.3+/4.5): `Scene Time → Seconds`; `Sample Index` (×2 + `Mix` dla interpolacji liniowej, `Clamp=on`); `index = Seconds / dt`. `Sample Index` nie interpoluje sam. `Store/Named Attribute` + `me.attributes.new(type='FLOAT', domain='POINT')` + `foreach_set('value', np_float32)` do budowy danych z numpy. Builder: `node_group.interface.new_socket(...)` — **API 4.0+ (stare `ng.inputs/outputs` USUNIĘTE, kod 3.x rzuci AttributeError)**. Koszt samplingu kilku indeksów/klatkę pomijalny. Obwiednie beatów: **prekomputować w numpy** jako atrybut (`exp(-dt_event/tau)` lub `clamp(1 - dt/decay)`), unika drogiego proximity per-frame.

### Prior-art (sklonowane do `research/prior-art/` — study-only, gitignored, NIE wendorowane)

Cztery projekty zbadane w kodzie. **Twardy wniosek: żaden NIE de-ryzykuje Spike 2 (most B, `Seconds/dt → Sample Index`)** — rdzeń trzeba zrobić od zera (żywy Blender + Manual).

- **`negdo/Sound_Nodes` (GPL-3.0, Blender 3.4):** robi **most A** (keyframe-bake + driver), nie B — zero `Sample Index`/`Scene Time`/mesh-attribute. **Blueprint FALLBACKU-A**, nie walidacja B. Waliduje koncept `beat_env`: ich „Beats Triangle" = bliskość-do-najbliższego-beatu = nasze `clamp(1-dt/decay)` (w Lite tylko opisany w README, nie zaimplementowany → **LEARN, nie LIFT**). API socketów 3.x (`.outputs.new`) **usunięte w 4.0** — nie kopiować. Daje wzorzec keyframe-asercji dla Unit 10 pod fallback-A (czyt. `fcurves`). GPL → tylko `blender_script/`, reimplementacja z README.
- **`kessoning/Audio-Offline-Analysis` (MIT, 2023, martwy):** ~3 linie transferu — max-scaling `arr/np.max(arr)` (jeden skalar, NIE per-band STFT, **bez guardu zera**) + `round(beat_sec*fps)`. Potwierdza arytmetykę Unit 5; potwierdza max-scaling jako **start** Spike 1, nie zamyka (brak percentyla, brak oceny klipu; `librosa.load` resampluje do 22050 → maskuje problem sr, który MY obsługujemy jawnie). Nie rozwiązuje per-band normalizacji ani `dt`-z-`times[]`.
- **`tom-malaeasy/Audio2Blender` (GPL-3.0, Blender 2.80, beta):** potwierdza **kanał mesh-as-data** (`mesh.attributes.new('FLOAT','POINT')` + `foreach_set`) = koncept Unit 6. **README kłamie** o „sends to Geometry Nodes" — zero budowania node-group, Unit 7 nietknięty. Realtime (`sounddevice`, timery) = **AVOID** (łamie INV1). `bl_info` 2.80 → nie wzorzec API.
- **`miolini/blender-auto-render` (BRAK licencji = all rights reserved):** **SKIP** — nie wolno kopiować. Orkiestracja = uboższy podzbiór `BlenderProjectManager` (bez stderr-capture, bez `--` separatora). Direct-mp4-mux = anty-wzorzec vs frames→FFmpeg-mux. EEVEE legacy API usunięte w 4.2+. Render-block bez audio. → Reużyj cinemon `project_setup.py` (H264+AAC) + CGWire frames-then-mux.

### Verified Absence

Repo-wide grep: zero `geometry.?node`, `node_group`, `MCP`, `bmesh`, `bpy.data.meshes`. Cały kod Blendera w repo to **VSE 2D only**. Moduł 3D GN jest **greenfield**.

## Key Technical Decisions

- **Nowy pakiet workspace `cymatic`** (decyzja użytkownika, Otwarte 1): member `packages/cymatic/`, zależny od `setka-common` + `beatrix`. Powód: config `cinemon` mocno sprzężony z VSE (`strip_animations` po nazwie pliku, `layout`, `AnimationSpec`) — nic z tego nie pasuje do sceny GN; czysty rozdział paradygmatów. Reużycie: `RecordingStructureManager`, `AudioValidator`, wzorzec subprocess + `--config`, wzorzec `try/except ImportError: bpy=None` + conftest Mock. Nazwa robocza, do zmiany przy scaffoldzie.
- **Most B (mesh-jako-dane)** z fallbackiem A: dane jako mesh (N wierzchołków, X=czas, float-atrybuty); drzewo GN próbkuje przez `Sample Index`. Gdyby Spike 2 zabił B → fallback do podejścia A (keyframe+drivery). (origin: Decyzja 4)
  - **Blast radius fallbacku-A** (review: adversarial — to NIE „adaptacja parametru", to ~40% przepisania buildu): pod A **znikają** Unit 6 (data-object), Unit 7 (GN sampler) i cała sekcja interpolacji w High-Level Technical Design; Unit 10 zmienia strategię z „odczyt kanału GN" na „odczyt czasów keyframe F-curve". **Keyframe-based asercja Unit 10 pod A NIE jest jeszcze zaprojektowana** — to dług dziedziczony przy kill. Konsekwencja dla bramki: zbiorcza reguła go/no-go traktuje pojedynczy fallback-A jako tani, a jest kosztowny — przy kill Spike 2 świadomie zważyć, czy kontynuować, nie kontynuować domyślnie.
- **`dt` czytany z `times[]` per-track, NIE hardkodowany.** `dt = times[1] - times[0]` (równoważne `hop_length/sample_rate`). Most B czyta `sample_rate` i wyprowadza index z faktycznej siatki — inaczej sync przejdzie spike na jednym sr i pęknie na produkcji o innym sr. (origin: Otwarte 3) — **najwyższe ryzyko detalu**.
- **Normalizacja per-track w nowym module** (numpy, deterministyczna, raz na analizę): percentyl/max do 0..1. Cel MVP = czytelność W OBRĘBIE utworu. `beatrix` nietknięty. (origin: Decyzja 5)
- **Obwiednie beatów/peaków prekomputowane w numpy** (podejście C z researchu): osobne float-atrybuty `beat_env`/`peak_env`, samplowane tym samym `Sample Index` co pasma. Cała semantyka zdarzeń poza grafem.
- **Sync weryfikowany z DANYCH, nie z obrazu** (wymuszone ograniczeniem MCP): harness czyta czasy keyframe / próbkuje stan na klatkach beatów i liczy odchyłkę w klatkach. MCP screenshot służy tylko kompozycji/lookowi (statyka). (origin: Decyzja 2, doprecyzowane researchem)
- **Config MVP = dataclass**, serializowany do pliku przekazywanego przez `--config` (nie YAML cinemon). (origin: Decyzja zakresu, Otwarte 4)
- **Artefakt reprodukowalny = builder.py + dataclass params** (commit); `.blend` produkt uboczny. (origin: Otwarte 5, INV2)
- **Render headless osobno** (nie przez MCP), do `blender/render/` przez `ensure_blender_dir()`.
- **`fps` pochodzi z `VisualizerConfig`, NIE z analizy** (review: feasibility/scope/adversarial). `beatrix` **nie emituje `fps`** (zwraca tylko `duration`, `sample_rate`, `tempo`, `animation_events`, `frequency_bands`). `build_scene.py` ustawia `scene.render.fps` z tej samej wartości config, której używa harness sync (`round(beat_sec*fps)`) — inaczej time-based GN sampling (`Seconds/dt`, fps-niezależny) i frame-based asercja mogą się rozjechać. Default np. 30.
- **„Look freeze" — krok kodyfikacji** (review: adversarial INV2): look wyeksplorowany przez MCP MUSI być przepisany do `hybrid_v1.py` + `PresetParams` **i zweryfikowany**, że re-run buildera na tym samym `analysis.json` odtwarza zaakceptowaną klatkę (pixel/perceptual diff na klatce akceptacji). Pętla MCP może manipulować **tylko parametrami wyrażalnymi w `PresetParams`** — inaczej INV2 nie zachodzi. **R4 (akceptacja) bramkuje output BUILDERA, nie interaktywny `.blend`.**

## Open Questions

### Resolved During Planning

- **Gdzie żyje kod?** → Nowy pakiet workspace `cymatic` (decyzja użytkownika).
- **Mechanika GN time→index?** → `Scene Time → Seconds`, `index = Seconds/dt` (dt z `times[]`), `Sample Index`×2 + `Mix`, `Clamp=on`. (research framework-docs)
- **Reprezentacja zdarzeń?** → prekomputowane obwiednie decay w numpy jako atrybuty (podejście C).
- **Jak weryfikować sync skoro MCP nie pokazuje ruchu?** → asercja na danych (czasy keyframe / sampling na klatkach beatów), nie wizualnie.
- **Reproducible artifact?** → builder.py + dataclass params (origin: Otwarte 5).

### Deferred to Implementation

- **Wybór serwera MCP — ROZSTRZYGNIĘTE (Spike 3a):** oficjalny **Blender Lab MCP** (GPL-3.0), zainstalowany i zweryfikowany na Blenderze 5.1.2. Napęd: natywne narzędzia MCP w Claude Code (po reloadzie) LUB wprost przez socket `localhost:9876` (cienki klient). Nie ahujasid, nie własny bridge.
- **Ścieżka `blender_executable` na macOS** — POTWIERDZONE: `/Applications/Blender.app/Contents/MacOS/Blender`, **Blender 5.1.2** (nowszy niż target 4.3/4.5; API `interface` 4.0+ działa — Spike 2 PASS). `snap run blender` Linux-only. Default config dla tej maszyny = ścieżka macOS.
- **Dokładna wartość N** (tolerancja sync w klatkach, np. ≤2) — kalibracja przy harnessie sync (Unit 10), zależna od `dt` vs `1/fps`. N jest **stałą wewnętrzną harnessu (Unit 10)**, nie polem config (review: scope — przedwczesna powierzchnia konfiguracji); promować do config tylko gdy dane pokażą wariancję per-track.
- **Dokładna wartość K** (budżet iteracji stop-rule, np. 5) — ustalić przy **autonomicznej pętli MCP (Unit 11 / Faza C)**, po potwierdzeniu że Spike 3a przeszedł (review: coherence — K to parametr R5/Fazy C, nie Fazy B).
- **Zachowanie loadera przy `len(times) < 2`** (`dt = times[1]-times[0]` rzuci IndexError) — guard + jasny błąd dla zdegenerowanej/krótkiej analizy (review: feasibility — to najbardziej load-bearing wartość).
- **Dokładny kształt serializacji dataclass** (JSON vs prosty YAML bez maszynerii cinemon) — implementacja (Unit 4).
- **Metoda normalizacji** — **ROZSTRZYGNIĘTE Spike 1 (na realnym CC0 jazz, 48k):** kotwica **`p99`** (percentyl 99) — clamp_hi 1%, CV ~0.7 (bass/high) / ~0.4 (mid), mean ~0.32, odporna na pojedyncze transjenty (max-scaling zaniża zakres do mean ~0.25; p95 clampuje 5%). Per-band, deterministyczna, z guardem zera. Potwierdzić na ≥1 dodatkowym utworze innego gatunku.
- **Codec/container mp4** — dopasować do ustawień FFMPEG z `packages/cinemon/blender_addon/vse/project_setup.py` (Unit 9).
- **Mechanizm odczytu stanu kanału GN per-klatka w harnessie (Unit 10)** — czy `build_scene.py` eksportuje plik danych per-frame, czy harness biegnie wewnątrz Blendera (kolejny subprocess)? (review: scope — niejawne). Determinuje, czy Unit 10 to czysty test Pythona, czy wymaga subprocess.
- **Rozwiązanie `extracted_dir` dla `AudioValidator`** z `base_directory` (lub bezpośrednie `--analysis-file`/`--main-audio`) — Unit 5.
- **Czy nazwa `cymatic` trwa do MVP** czy rename przy scaffoldzie (rename mid-build = churn ścieżek importu) — decyzja przy Unit 4.

## Output Structure

    packages/cymatic/
    ├── pyproject.toml                         # member workspace, deps: setka-common, beatrix
    ├── src/cymatic/
    │   ├── __init__.py
    │   ├── config.py                          # dataclass: VisualizerConfig + PresetParams
    │   ├── analysis_loader.py                 # wczytanie JSON, AudioValidator, dt z times[]
    │   ├── normalization.py                   # per-track 0..1 + prekomputacja obwiedni
    │   ├── runner.py                          # host-side: subprocess blender + --config + render
    │   └── cli.py                             # entry point (np. cymatic-render)
    ├── blender_script/                        # wykonywane WEWNĄTRZ Blendera (import bpy)
    │   ├── build_scene.py                     # entry: --config → data-object + GN + scena + render
    │   ├── data_object.py                     # numpy → mesh + float-atrybuty (foreach_set)
    │   ├── gn_sampler.py                       # builder drzewa GN (node_group.interface)
    │   └── presets/
    │       └── hybrid_v1.py                    # jeden preset wizualny (look)
    └── tests/
        ├── conftest.py                        # mock_bpy + mock_subprocess (wzorzec cinemon)
        ├── test_normalization.py
        ├── test_analysis_loader.py
        ├── test_data_object.py
        ├── test_gn_sampler.py
        ├── test_runner.py
        └── test_sync_verification.py

> Drzewo to deklaracja zakresu, nie sztywne ograniczenie — implementacja może dostosować układ.

## High-Level Technical Design

> *Ilustruje zamierzone podejście, jako wskazówka kierunkowa do recenzji, NIE specyfikacja implementacji. Agent implementujący traktuje to jako kontekst, nie kod do odtworzenia.*

Przepływ danych (host-side → in-Blender):

```
*_analysis.json (beatrix)
        │
        ▼  analysis_loader.py     reużywa AudioValidator; czyta sample_rate, dt = times[1]-times[0]
   { duration, dt, bands(raw), beats[], energy_peaks[] }   # fps z VisualizerConfig, NIE z analizy
        │
        ▼  normalization.py        per-track 0..1 (percentyl/max), deterministyczne
   { bass_n[], mid_n[], high_n[], beat_env[], peak_env[] }   # obwiednie prekomputowane (numpy)
        │
        ▼  config.py               dataclass VisualizerConfig + PresetParams → serializacja
   config_file  ──►  runner.py  ──►  blender --background --python build_scene.py -- --config <file>
                                                  │
                          ┌───────────────────────┼───────────────────────────┐
                          ▼                        ▼                           ▼
                   data_object.py            gn_sampler.py                presets/hybrid_v1.py
              numpy → mesh N wierzch.    node_group GN:                scena: pasma→ciągła forma,
              X=czas, attrs:             Scene Time→Seconds            impulsy→akcenty (skala/błysk)
              bass_n,mid_n,high_n,       index = Seconds/dt
              beat_env,peak_env          Sample Index ×2 + Mix (Clamp)
                                          → bass/mid/high/beat/peak (interp.)
                          └───────────────────────┬───────────────────────────┘
                                                   ▼  render headless → blender/render/<name>.mp4
```

Interpolacja w GN (most B, rdzeń sync):

```
Scene Time.Seconds ──► [÷ dt] ──► index_f
   i0 = floor(index_f);  i1 = i0+1;  frac = index_f - i0
   v0 = SampleIndex(attr, i0, Clamp=on)
   v1 = SampleIndex(attr, i1, Clamp=on)
   value = Mix(v0, v1, frac)          # liniowa interpolacja między próbkami
```

## Implementation Units

> **Fazowanie:** Faza 0 (pożądalność) → Faza A (spike'y techniczne, bramki kill) → Faza B (build MVP) → Faza C (poza gate). Faza 0 i A MUSZĄ poprzedzić Fazę B. **Zbiorcza reguła go/no-go:** jeśli Spike 2 → fallback-A ORAZ Spike 3a → fallback-ręczny jednocześnie, projekt redukuje się do ręcznego ślęczenia nad driverami (to, co miał wyeliminować) → **bet martwy, przerwać** (origin: reguła zbiorcza).

### Faza 0 — Pożądalność (przed inżynierią)

- [x] **Unit 0: Spike — pożądalność outputu 3D (throwaway)**

**Goal:** Tanio potwierdzić, że abstrakcyjny wizualizer 3D to output, który twórca faktycznie chce — **zanim** ruszy jakikolwiek scaffold/spike techniczny.

**Requirements:** Warunek wstępny R4 (pożądalność przed inżynierią).

**Dependencies:** Brak.

**Approach:**
- Ręcznie w Blenderze (godziny): prosty throwaway `.blend` — kilka obiektów GN/keyframe sterowanych zgrubnie energią z jednego realnego `*_analysis.json`, render krótkiego klipu mp4. **Bez `cymatic`, bez scaffoldu, bez mostu B** — cel to obraz do oceny, nie architektura.
- Twórca ogląda klip i ocenia: czy ten typ wizualizacji jest warty budowania pełnego pipeline'u.

**Execution note:** Maksymalnie tani, jednorazowy. Nic z tego kodu nie trafia do produkcji.

**Test scenarios:**
- Test expectation: none — throwaway probe, brak zmiany behawioralnej do testowania. Output = decyzja twórcy.

**Verification (bramka kill):** Twórca uznaje typ outputu za wart budowania. **Kill → cały bet pada za grosze, przed inżynierią** (najtańszy możliwy punkt porzucenia; review: product — najdroższa porażka odkryta najpóźniej, ten spike ją przesuwa na początek).

**STATUS: PASS (2026-05-31).** Zbudowano działający artefakt wprost w żywym Blenderze 5.1.2 (napęd przez socket): 3 koncentryczne kręgi słupków (bass/mid/high) z przewijaną historią energii + świecący rdzeń pulsujący na `beat_env`, na realnych danych. **Sync potwierdzony** (wizualnie+słuchowo) na syntetycznym rytmie 120 BPM. Twórca: „jest synchronizacja, możemy działać". Skrypty: `research/build_visualizer_v1.py`, `research/build_visualizer_v2.py`.
> **Finding (do buildu):** domyślny `beat_division=8` w beatrix decymuje beaty ~8× → na 120s jazzu tylko 32 beaty (rzadkie pulsy). Wizualizer powinien wołać beatrix z **`beat_division=1`** (lub mapować `onsets`/`energy_peaks` na impulsy) dla gęstego, czytelnego rytmu.

### Faza A — De-ryzykowanie (spike'y z bramkami)

- [x] **Unit 1: Spike — normalizacja pasm (per-track 0..1)**

**Goal:** Potwierdzić, że deterministyczny per-track transform surowych magnitud STFT daje wizualnie czytelny ruch W OBRĘBIE utworu.

**Requirements:** R1 (część ciągła), INV1.

**Dependencies:** Brak (czysty numpy + istniejące `*_analysis.json`).

**Files:**
- Create (prototyp, może wylądować w `normalization.py`): `packages/cymatic/src/cymatic/normalization.py`
- Test: `packages/cymatic/tests/test_normalization.py`

**Approach:**
- Wczytać `frequency_bands.{bass,mid,high}_energy` z realnego `*_analysis.json`.
- Porównać warianty: max-scaling, percentyl (np. 95/99), log+percentyl. Wybrać deterministyczny.
- Ocena czytelności: rozkład wartości po normalizacji (czy ruch widoczny, czy nie klipuje do 0/1 przez większość czasu).

**Execution note:** Spike eksploracyjny — wynik to decyzja metody + dane, nie produkcyjny moduł. Walidacja w `ce:work`.

**Test scenarios:**
- Happy path: znormalizowane pasmo mieści się w [0,1], `min≈0`, `max≈1` dla wybranej metody.
- Edge case: pasmo o stałej (niemal zerowej) energii — brak dzielenia przez zero, wynik zdefiniowany (np. wszystkie 0).
- Determinizm: dwukrotna normalizacja tych samych danych → identyczny wynik (bit-for-bit).

**Verification (bramka kill — MIERZALNA, nie estetyczna):** Na ≥1 realnym utworze, dla wybranej metody, **udział klatek sklipowanych do 0/1 < X%** ORAZ **współczynnik zmienności (CV) energii > Y** (X, Y ustalone z góry, np. X=20%, Y dobrane na podglądzie). **STATUS: PASS (2026-05-31)** na CC0 jazz 48k — kotwica `p99`: clamp_hi 1%, CV 0.4–0.7, mean 0.32. Wszystkie warianty (max/p99/p95) zaliczyły; p99 wybrany. **Kill** jeśli żadna deterministyczna metoda nie spełnia progu (review: adversarial — „czytelny" to osąd estetyczny, nie bramka; bez progu spike jest nie-do-obalenia). Jeśli progu nie da się sensownie ustalić → spike degraduje do **doradczego** (twardy output = „istnieje wybrana metoda deterministyczna"), nie kill-gate (origin: Spike 1).

---

- [x] **Unit 2: Spike — GN time-sampling (most B) na ≥2 sr**

**Goal:** Potwierdzić, że drzewo GN czyta atrybut po czasie z poprawnym `time→index`, na ≥2 utworach o RÓŻNYM `sample_rate`.

**Requirements:** R2, R3 (rdzeń), INV2.

**Dependencies:** Brak — spike może użyć syntetycznej tablicy `np.linspace(0,1,N)` zamiast znormalizowanych danych beatrix (review: scope — Unit 1 nie blokuje; realne dane wchodzą dopiero w Unit 6). Może biec równolegle do Unit 1.

**Files:**
- Create (prototyp → `data_object.py` + `gn_sampler.py`): `packages/cymatic/blender_script/data_object.py`, `packages/cymatic/blender_script/gn_sampler.py`
- Test: `packages/cymatic/tests/test_gn_sampler.py` (struktura node tree przez mock bpy)

**Approach:**
- Zbudować minimalny data-object: mesh N wierzch., X=czas, atrybut `bass_n` (`me.attributes.new(type='FLOAT', domain='POINT')` + `foreach_set`).
- Zbudować minimalne drzewo GN: `Scene Time→Seconds`, `÷ dt`, `Sample Index`×2 + `Mix`, `Clamp=on`.
- **`dt` z `times[1]-times[0]`** (NIE stała). Przetestować na utworze 22050 Hz i 48 kHz.
- Asercja na danych: dla wybranych klatek wartość z GN == znormalizowana wartość beatrix w tym czasie (z tolerancją interpolacji).

**Execution note:** Najpierw asercja poprawności `time→index` na dwóch sr — to jest cały sens spike'a.

**Test scenarios:**
- Happy path (mock bpy): builder tworzy `node_group` z socketami przez `interface.new_socket`, węzły `GeometryNodeInputSceneTime`, `GeometryNodeSampleIndex` istnieją, `clamp=True`.
- Integration (żywy Blender, ręcznie w spike'u): dla 22050 Hz wartość@frame odpowiada `bass_n[round(sec/dt)]` ±interp.
- Integration: ten sam test dla 48 kHz — index liczony z `dt` tego pliku, nie z poprzedniego.
- Edge case: czas przed pierwszą / po ostatniej próbce → `Clamp` zwraca wartość skrajną, nie 0/czarną klatkę.

**Verification (bramka kill):** Stan wizualizacji@dowolna klatka odpowiada danym beatrix na **obu** sr. **Kill → fallback do podejścia A** (keyframe+drivery), reszta planu adaptuje się do A (origin: Spike 2).

**STATUS: PASS (2026-05-31)** na żywym **Blenderze 5.1.2**, realny CC0 jazz, **OBA sr**. Graf: `Scene Time→Seconds → ÷dt → Sample Index×2 + Mix(frac), Clamp=on`, `index` z `dt` każdego utworu. Read-back przez depsgraph (probe vertex Z): **max abs_err = 5.96e-08** (precyzja float) na 48k (dt=0.010667) i 44k (dt=0.011610). Most B potwierdzony empirycznie; API `node_group.interface.new_socket` (4.0+) działa na 5.x. Skrypt: `research/spike2_gn_sampling.py`. **Fallback-A zdjęty ze stołu dla rdzenia.**

---

- [x] **Unit 3: Spike — MCP/bridge (binarny 3a)**

**Goal:** Potwierdzić binarnie, że wybrana ścieżka MCP/bridge umie uruchomić Python (`bpy`) w żywym Blenderze i zwrócić screenshot viewportu, którego agent „widzi".

**Requirements:** Warunek wstępny R5 (Unit 11 zależy od pass Spike 3a). Kill → fallback-ręczny zastępujący autonomiczną pętlę; MVP (R4) nadal osiągalny bez tego spike'a.

**Dependencies:** Brak (niezależny od Unit 1/2).

**Files:**
- Create (notatka/skrypt spike'a): `docs/solutions/` (po spike'u) lub `packages/cymatic/blender_script/` smoke-skrypt.

**Approach:**
- Ocenić 3 opcje: `ahujasid/blender-mcp` (gotowy, ~800px screenshot, niesandboxowany `execute_blender_code`), oficjalny Blender Lab MCP, **własny cienki socket-bridge / headless `bpy`** (sandbox pod kontrolą, spójny z istniejącym headless w repo).
- Smoke test: uruchom trywialny `bpy` (utwórz kostkę), pobierz screenshot, potwierdź że obraz wraca do agenta.
- Na macOS: potwierdź ścieżkę Blendera (nie `snap`), local-network permission dla socketu loopback.
- **Kryteria bezpieczeństwa (review: security — 10 min source review, nie blokują spike'a):** (1) czy addon robi połączenia wychodzące poza loopback? (2) czy źródło jest przeglądalne i sprawdzone? (3) socket binduje **tylko `127.0.0.1`** (nigdy `0.0.0.0`) i żyje **tylko na czas sesji autoringu** (nie trwały demon); (4) czy przyjmuje połączenia od dowolnego procesu lokalnego, czy tylko od rodzica.

**Execution note:** Binarny, godziny. NIE buduj tu wizualizera — tylko potwierdź zdolność.

**Test scenarios:**
- Happy path: `execute_blender_code` tworzy obiekt; `get_viewport_screenshot` zwraca obraz widziany przez agenta.
- Error path: długi skrypt nie zawiesza trwale UI / timeout obsłużony.

**Verification (bramka kill):** Python+screenshot działają w żywym Blenderze na macOS. **Kill → fallback:** agent generuje setup GN raz, człowiek dostraja ręcznie (MVP nadal osiągalny przez builder, bez autonomicznej pętli). **3b (zbieżność pętli) NIE jest tu bramką — to Faza C / R5.** (origin: Spike 3a/3b)

**STATUS: PASS (2026-05-31).** Serwer **ROZSTRZYGNIĘTY: oficjalny Blender Lab MCP** (`blender.org/lab`, GPL-3.0) — już zainstalowany: addon `lab_blender_org/mcp` w Blenderze 5.1.2 (socket non-blocking `localhost:9876`, `weak_sandbox.py`) + rozszerzenie Claude Desktop `blmcp`. Zweryfikowane end-to-end: `execute_blender_code` zwrócił `{version:5.1.2, objects:[Camera,Cube,Light]}`; `bpy.ops.screen.screenshot` → PNG 2532×1834, agent odczytał obraz. Narzędzia: `execute_blender_code`, `get_screenshot_of_window/area_as_image`, `render_viewport_to_path`, `search_manual_docs`, summaries blendfile. **Podpięty do Claude Code** (`claude mcp add blender`, local scope, ✓ Connected — natywne po reloadzie). **Uproszczenie:** można też napędzać wprost przez socket (`connection.py`, ~95 linii, null-byte JSON `type:execute`) — bez warstwy serwera MCP; obniża zależność Unit 11.

> **Przed Fazą B — sprawdź zbiorczą regułę go/no-go:** jeśli Spike 0 (pożądalność) OK, Spike 1 OK, Spike 2 OK i (Spike 3a OK LUB akceptacja fallbacku-ręcznego dla MVP) → wejdź w Fazę B. **Spike 3a kill blokuje tylko Fazę C / Unit 11 — NIE Fazę B**; MVP osiągalny bez autonomicznej pętli (review: coherence). Kill Spike 2 → patrz „Blast radius fallbacku-A" (Key Technical Decisions): świadoma decyzja, nie auto-kontynuacja.

### Faza B — Build MVP

- [x] **Unit 4: Scaffold pakietu + config dataclass**

**Goal:** Utworzyć pakiet workspace `cymatic` z podziałem host/in-Blender i dataclass config.

**Requirements:** Fundament dla R1–R4, INV2.

**Dependencies:** Decyzja o nazwie pakietu (potwierdzić przy scaffoldzie).

**Files:**
- Create: `packages/cymatic/pyproject.toml`, `packages/cymatic/src/cymatic/__init__.py`, `packages/cymatic/src/cymatic/config.py`, `packages/cymatic/tests/conftest.py`
- Modify: `pyproject.toml` (root — dodać member do `[tool.uv.workspace]` i `[tool.uv.sources]`)

**Approach:**
- Member workspace, deps `setka-common` + `beatrix` przez `{ workspace = true }`. Backend hatchling (jak cinemon).
- Podział: `src/cymatic/` (host, absolute imports) vs `blender_script/` (in-Blender, `try/except ImportError: bpy=None`).
- `conftest.py`: skopiować wzorzec `mock_bpy` + `mock_subprocess` z `packages/cinemon/tests/conftest.py`; wstrzyknąć `blender_script/` na `sys.path`.
- `config.py`: `@dataclass VisualizerConfig` (ścieżki: analysis_file, output_mp4, base_directory; `fps` (default np. 30); `resolution`; `blender_executable`) + `@dataclass PresetParams` (paleta, prymityw geometrii, intensywność akcentów, `decay`/`tau`). **`n_tolerance_frames` NIE jest tu** — to stała wewnętrzna harnessu (Unit 10), nie powierzchnia config (review: scope). Serializacja do pliku **przez `tempfile.NamedTemporaryFile`** (review: security — sprzątany po subprocess, nie zostawia layoutu FS na dysku) i deserializacja w `build_scene.py`.
- **Packaging:** `blender_script/` poza wheel (`packages = ['src/cymatic']`, jak `blender_addon/` w cinemon); `runner.py` lokalizuje `build_scene.py` przez `Path(__file__).parent.parent.parent / 'blender_script' / 'build_scene.py'` (wzorzec `BlenderProjectManager`). Root `pyproject.toml`: dodać `packages/cymatic/tests` do `testpaths` i `packages/cymatic/src` do `pythonpath` (review: feasibility — inaczej `uv run pytest` nie zbierze pakietu).

**Patterns to follow:** `packages/cinemon/pyproject.toml` (struktura), `packages/cinemon/tests/conftest.py` (mocki), `packages/common/src/setka_common/config/yaml_config.py` (`ProjectConfig` jako referencja pól — fps/resolution/render_output/base_directory).

**Test scenarios:**
- Happy path: `VisualizerConfig` round-trip serializacja↔deserializacja zachowuje wszystkie pola.
- Edge case: brak opcjonalnego pola (`resolution=None`) → sensowny default.
- Happy path: `uv sync` widzi nowy pakiet (smoke importu `import cymatic`).

**Verification:** Pakiet importowalny, testy uruchamiają się z mock bpy, config round-trip przechodzi.

---

- [x] **Unit 5: Loader analizy + normalizacja + prekomputacja obwiedni**

**Goal:** Host-side moduł: wczytuje `*_analysis.json`, wybiera audio, normalizuje pasma per-track, prekomputuje obwiednie beatów/peaków, wyprowadza `dt` z `times[]`.

**Requirements:** R1, R3 (dt), INV1.

**Dependencies:** Unit 1 (metoda normalizacji), Unit 4 (config).

**Files:**
- Create: `packages/cymatic/src/cymatic/analysis_loader.py`, `packages/cymatic/src/cymatic/normalization.py` (finalizacja prototypu z Unit 1)
- Test: `packages/cymatic/tests/test_analysis_loader.py`, `packages/cymatic/tests/test_normalization.py`

**Approach:**
- `analysis_loader`: ścieżka JSON pochodzi **wprost z `VisualizerConfig.analysis_file`** — NIE z `get_analysis_file_path()` (review: scope — jego sygnatura to `(video_path)` i derywuje stem z pliku wideo, nie z katalogu nagrania; niezgodne z wejściem cymatic). Wybór audio: `AudioValidator.detect_main_audio(extracted_dir, ...)` — **uwaga: bierze `extracted/`, nie katalog nagrania**; rozwiązać `extracted_dir` z `base_directory` przed wywołaniem (lub przyjąć audio z config). **Wyprowadzić `dt = times[1] - times[0]`** (walidować spójność z `hop_length/sample_rate`; **guard na `len(times) < 2`** → jasny błąd). Odczytać `sample_rate`, `duration`. **`fps` z `VisualizerConfig.fps` (beatrix NIE emituje `fps`)**, nie z JSON.
- `normalization`: deterministyczny transform 0..1 (metoda z Unit 1); prekomputacja `beat_env`/`peak_env` z `animation_events.{beats,energy_peaks}` (np. `clamp(1 - dt_event/decay)` lub `exp(-dt_event/tau)`) na siatce `times[]`. **Uwaga (review: adversarial):** `energy_peaks` w beatrix to **wyłącznie peaki basu** (`_find_bass_peaks`) — `peak_env` jest strukturalnie bass-driven; na utworach bass-light `peak_env` będzie rzadkie/puste, a jedynym pozostałym impulsem jest `beats` (siatka tempa). Preset (Unit 8) nie powinien zakładać gęstych peaków.
- Output: struktura gotowa do zakodowania jako atrybuty (równej długości tablice numpy).

**Patterns to follow:** `packages/cinemon/blender_addon/vse/animation_compositor.py` (`_extract_events` — mapowanie triggerów na klucze eventów), `AudioValidator` API.

**Test scenarios:**
- Happy path: dla fixture JSON wszystkie pasma znormalizowane do [0,1], długości == `len(times)`.
- Edge case (R3): dwa fixture o różnym `sample_rate` (22050, 48000) → `dt` różne, poprawnie wyprowadzone z `times[]`, nie z założonej stałej.
- Edge case: beat dokładnie na próbce vs między próbkami → obwiednia szczytuje we właściwym indeksie.
- Error path: brak pliku analizy → `FileNotFoundError`; wiele plików audio bez wskazania → propagacja `MultipleAudioFilesError`.
- Error path: `len(times) < 2` → jasny błąd (nie IndexError z `times[1]`).
- Edge case: pusta lista `energy_peaks` → `peak_env` same zera, brak wyjątku.
- Happy path: `fps` czytane z `VisualizerConfig`, NIE z JSON (brak klucza `fps` w analizie nie powoduje błędu).
- Integration: pełne przejście loader→normalizacja na realnym `*_analysis.json` daje tablice równej długości gotowe dla data-object.

**Verification:** Dla ≥2 utworów o różnym sr loader produkuje spójne, znormalizowane, równej długości tablice z poprawnym `dt`.

---

- [x] **Unit 6: Data-object builder (numpy → mesh + atrybuty)** *(in-Blender)*

**Goal:** Zbudować w Blenderze obiekt-danych: mesh N wierzch., X=czas, float-atrybuty `bass_n/mid_n/high_n/beat_env/peak_env`.

**Requirements:** R1, INV2. (R2/R3 weryfikowane w Unit 10, nie tu — Unit 6 buduje tylko strukturę danych.)

**Dependencies:** Unit 2 (potwierdzony wzorzec), Unit 5 (dane).

**Files:**
- Create: `packages/cymatic/blender_script/data_object.py`
- Test: `packages/cymatic/tests/test_data_object.py` (mock bpy — asercje struktury)

**Approach:**
- `me.vertices.add(N)`; `co[0::3] = arange(N)*dt` (X=czas); `me.vertices.foreach_set("co", co)`.
- Per kanał: `me.attributes.new(name, type='FLOAT', domain='POINT')` + `attr.data.foreach_set("value", np.ascontiguousarray(arr, float32))`.
- Jeden obiekt, wiele atrybutów (jeden „data object", wiele kanałów).

**Patterns to follow:** wzorzec `foreach_set` z numpy (research framework-docs); `try/except ImportError: bpy=None`.

**Test scenarios:**
- Happy path (mock bpy): builder woła `attributes.new` dla 5 kanałów, `foreach_set` z buforem długości N.
- Edge case: N==len(times) zachowane; bufor float32, C-contiguous.
- Integration (żywy Blender, manualnie/Unit 2): odczyt atrybutu po indeksie == wartość wejściowa.

**Verification:** Data-object ma N wierzchołków i 5 poprawnych float-atrybutów; X-pozycje == `arange(N)*dt`.

---

- [x] **Unit 7: GN sampler tree builder** *(in-Blender)*

**Goal:** Programowo zbudować drzewo GN próbkujące data-object po czasie i wystawiające interpolowane `bass/mid/high/beat/peak`.

**Requirements:** R2, R3.

**Dependencies:** Unit 6 (data-object).

**Files:**
- Create: `packages/cymatic/blender_script/gn_sampler.py`
- Test: `packages/cymatic/tests/test_gn_sampler.py` (mock bpy — struktura)

**Approach:**
- `bpy.data.node_groups.new(..., 'GeometryNodeTree')`; sockety przez **`ng.interface.new_socket(name, in_out, socket_type)`** (API 4.0+).
- Węzły: `GeometryNodeInputSceneTime` (Seconds), `GeometryNodeMath` (DIVIDE: Seconds/dt), `GeometryNodeSampleIndex`×2 (`data_type='FLOAT'`, `domain='POINT'`, `clamp=True`), `Mix` (frac). Per kanał wpięty `GeometryNodeInputNamedAttribute`.
- `dt` przekazane jako wartość węzła (z config), spójne z data-object.

**Patterns to follow:** schemat interpolacji z sekcji High-Level Technical Design; API `node_group.interface` (research).

**Test scenarios:**
- Happy path (mock bpy): tworzone węzły o właściwych bpy id; sockety przez `interface.new_socket` (NIE `ng.inputs`); `clamp=True`, `data_type='FLOAT'`.
- Edge case: builder pod 4.x — brak użycia usuniętego `ng.inputs/outputs`. **UWAGA (review: feasibility):** zwykły `Mock` fabrykuje każdy atrybut, więc `mock_ng.inputs` i `mock_ng.interface` są nieodróżnialnie truthy — test mockowy NIE wykryje regresji 3.x→4.x. Asercja realna tylko w żywym Blenderze (Unit 2 spike). W teście mockowym: asercja na ścieżce kodu (np. `spec`-owany mock interfejsu) lub jawny grep, nie poleganie na fabrykowanym atrybucie.
- Integration (Unit 2): interpolacja liniowa między próbkami daje wartość pośrednią dla czasu między indeksami.

**Verification:** Drzewo GN buduje się bez błędu, próbkuje 5 kanałów jednym indeksem, interpoluje liniowo.

---

- [x] **Unit 8: Preset wizualny + montaż sceny** *(in-Blender)*

**Goal:** Jeden hybrydowy preset: pasma → ciągła forma/ruch tła, impulsy (beat/peak) → dyskretne akcenty (skala/błysk/wyrzut). Codyfikowany w builderze.

**Requirements:** R1, INV2. (Akceptacja R4 zachodzi na wyrenderowanym klipie z Unit 9, nie tu.)

**Dependencies:** Unit 7 (sampler wystawia kanały).

**Files:**
- Create: `packages/cymatic/blender_script/presets/hybrid_v1.py`, `packages/cymatic/blender_script/build_scene.py` (orkiestracja: parse `--config` → data_object → gn_sampler → preset → [render w Unit 9])
- Test: `packages/cymatic/tests/test_data_object.py`/dedykowany (mock bpy — montaż struktury)

**Approach:**
- Wystawione kanały GN sterują: ciągłe pasma → deformacja/instancje/skala formy; `beat_env`/`peak_env` → impulsy (skok skali, emisja, błysk materiału).
- `PresetParams` (paleta, prymityw, intensywność) wpięte jako wejścia.
- Look hybrydowego presetu autorowany **bezpośrednio przez dewelopera** w `hybrid_v1.py`. Screenshoty MCP mogą **opcjonalnie** wspomóc statyczny przegląd kompozycji, ale **NIE są wymagane** do zaliczenia Unit 8 (review: scope/coherence — autonomiczna pętla to Unit 11/Faza C, ten unit nie zależy od pass Spike 3a). Finalny look **zapisany w builderze** (źródło prawdy, „look freeze" — patrz Key Technical Decisions/INV2), nie w `.blend`.
- `build_scene.py` parsuje `--config` ze `sys.argv` (wzorzec `vse_script.py`).

**Execution note:** MVP NIE zależy od MCP ani od autonomicznej zbieżności pętli (to R5/Faza C). Preset musi dać się zbudować i wyrenderować czysto z samego buildera.

**Test scenarios:**
- Happy path (mock bpy): `build_scene.main()` parsuje `--config`, woła data_object + gn_sampler + preset w kolejności, zwraca 0.
- Edge case: brak `--config` → czytelny błąd, kod != 0.
- Integration (żywy Blender): scena renderuje pojedynczą klatkę bez błędu; akcent widoczny przy `frame_set` na czas beatu.

**Verification:** Z config + data-object powstaje scena 3D, w której (a) ciągła energia i (b) impulsy beat/peak są widocznie sterowane (R1).

---

- [x] **Unit 9: Host-side runner + render do mp4**

**Goal:** Host-side: zbudować komendę subprocess, uruchomić Blender headless, wyrenderować mp4 do `blender/render/`.

**Requirements:** R4, INV2.

**Dependencies:** Unit 4 (config), Unit 8 (build_scene).

**Files:**
- Create: `packages/cymatic/src/cymatic/runner.py`, `packages/cymatic/src/cymatic/cli.py`
- Test: `packages/cymatic/tests/test_runner.py` (mock subprocess)

**Approach:**
- Wzorzec `BlenderProjectManager`: `[blender_executable, "--background", "--python", build_scene.py, "--", "--config", <file>]`, `subprocess.run(..., capture_output=True, text=True, check=True)`, `RuntimeError` na `CalledProcessError` (stderr).
- **macOS: `blender_executable` z config (jawna ścieżka), NIE `snap run`.** Zachować gałąź snap dla Linuxa.
- Output przez `RecordingStructureManager.ensure_blender_dir()` → `blender/render/<name>.mp4`. Render headless (nie MCP). **Render-block: kopiować z `packages/cinemon/blender_addon/vse/project_setup.py`** (kanoniczny: `FFMPEG`/`MPEG4`/`H264`/`HIGH` + audio `AAC`/192/48000) — NIE z `blender-auto-render` (bez audio, MKV/AV1, brak licencji). Rozważyć **frames→FFmpeg-mux** (PNG → `ffmpeg`) zamiast bezpośredniego muxera Blendera (pewniejsze; setka ma FFmpeg 4.4+; review prior-art + CGWire 2026).
- `build_scene.py` ustawia `scene.render.fps` z `VisualizerConfig.fps` — ta sama wartość, której używa harness sync (Unit 10), by time-based sampler i frame-based asercja nie rozjechały się.
- CLI entry point (np. `cymatic-render <recording_dir> [--main-audio ...]`).

**Patterns to follow:** `packages/cinemon/src/cinemon/project_manager.py` (subprocess, separator `--`, obsługa błędów), `RecordingStructureManager`.

**Test scenarios:**
- Happy path (mock subprocess): runner buduje poprawną komendę z `--config` i ścieżką build_scene; sukces → ścieżka mp4.
- Edge case: `blender_executable="blender"` na Linux → gałąź `snap run`; jawna ścieżka → bezpośrednio.
- Error path: `CalledProcessError` → `RuntimeError` z treścią stderr.
- Edge case: brak `blender/render/` → `ensure_blender_dir()` tworzy.
- Integration: pełny przebieg na fixture recording (mock subprocess) generuje oczekiwaną ścieżkę output zgodną ze strukturą katalogów.

**Verification:** Runner odpala Blender headless i produkuje mp4 w `blender/render/` (na realnym Blenderze — manualnie).

---

- [x] **Unit 10: Harness weryfikacji sync (z danych)**

**Goal:** Obiektywnie zmierzyć, że akcenty wizualne padają w ±N klatek od beatów/peaków beatrix — z danych, nie z obrazu.

**Requirements:** R2, R3.

**Dependencies:** Unit 7/8 (scena z akcentami), Unit 5 (dane referencyjne).

**Files:**
- Create: `packages/cymatic/src/cymatic/sync_verification.py` (lub w `tests/`)
- Test: `packages/cymatic/tests/test_sync_verification.py`

**Approach:**
- Strategia z danych (wymuszona ograniczeniem MCP): w żywym Blenderze `frame_set(f)` na klatki wokół beatów; odczytać stan kanału impulsu (lub czasy keyframe F-curve, jeśli fallback A) i znaleźć klatkę szczytu akcentu.
- Odchyłka = |klatka_szczytu - round(beat_sec * fps)|. Asercja ≤ N.
- **Mierzyć na ≥2 utworach o RÓŻNYM sr** (R3): potwierdzić, że `dt`-based index trzyma sync na obu.
- Skalibrować N (np. ≤2) — zależne od `dt` vs `1/fps` (kwantyzacja STFT to dolna granica). N = stała wewnętrzna harnessu (nie config).
- **Asercja spójności fps:** `config.fps == scene.render.fps == fps użyte w `round(beat_sec*fps)`** — chroni przed dryfem time-based vs frame-based (review: feasibility/adversarial).
- **Zakres tego dowodu (review: adversarial — szczerość kryterium 2):** obwiednia jest prekomputowana w numpy i samplowana po indeksie, więc ten harness weryfikuje przede wszystkim **arytmetykę `Seconds/dt` i rozmieszczenie obwiedni** (częściowo pokrywa Unit 2/Unit 5), oraz kwantyzację `dt` vs `1/fps`. **NIE** dowodzi percepcyjnego „akcent widać na beacie" — easing presetu, motion blur i liniowe rozmycie impulsu między próbkami (`dt` ~11–23 ms) mogą zmiękczyć akcent. Percepcyjna weryfikacja należy do akceptacji twórcy (R4), nie do tego harnessu. Kryterium MVP 2 = dowód timingu danych, nie timingu wizualnego — patrz present-finding poniżej.

**Test scenarios:**
- Happy path: dla syntetycznych danych (beat na znanym czasie) szczyt impulsu wypada w ±N klatek.
- Edge case (R3): test na 22050 Hz i 48 kHz — sync trzyma na obu (NIE tylko na tym, na którym przeszedł spike).
- Edge case: beat blisko końca utworu → brak indeksu poza zakresem (Clamp).
- Error path: utwór bez beatów → harness raportuje brak, nie crash.

**Verification (gate R2/R3):** Na ≥2 utworach różnego sr wszystkie akcenty w ±N klatek. To **obiektywny** dowód sync (kryterium MVP 2 i 3).

### Faza C — Poza gate MVP (zależne od Spike 3a)

- [ ] **Unit 11: Autonomiczna pętla autoringu MCP (R5)**

**Goal:** Sformalizować pętlę build→screenshot→ocena→popraw tak, by zbiegała look bez ręcznej ingerencji w node'y w budżecie ≤K iteracji.

**Requirements:** R5 (Faza 2).

**Dependencies:** Unit 3 (Spike 3a pass), Unit 8 (preset jako punkt startowy).

**Files:**
- Create: `packages/cymatic/` (orkiestracja pętli — host-side), rubryka oceny kompozycji.

**Approach:**
- Pętla: agent buduje/poprawia look przez `execute_blender_code`, pobiera `get_viewport_screenshot` (statyka, ~800px), ocenia wg **konkretnej, falsyfikowalnej rubryki** (kadr, occlusion, liczba instancji, obecność akcentu@frame), poprawia.
- **Sync NIE oceniany z obrazu** — zostaje w Unit 10 (dane). Pętla = tylko kompozycja/look.
- Budżet ≤K iteracji; po K bez akceptacji → fallback (generuj-raz + ręczne). Trzymać najnowsze 1-2 screenshoty w kontekście (koszt obrazu).

**Test scenarios:**
- Happy path: pętla wykonuje ≤K iteracji, każda z konkretną oceną; zwraca zaakceptowany look lub fallback.
- Edge case: brak zbieżności w K → czysty fallback, nie nieskończona pętla.

**Verification (R5):** Pętla zbiega look w ≤K bez ręcznej edycji node'ów. **To kryterium Fazy 2, poza gate MVP** (origin: kryterium 5).

## System-Wide Impact

- **Interaction graph:** Nowy pakiet jest **dodatkowym konsumentem** `beatrix` obok `cinemon`. Reużywa `setka-common` (`RecordingStructureManager`) i `beatrix` (`AudioValidator`). Brak modyfikacji `beatrix`/`cinemon` (INV1). (`MediaDiscovery` NIE jest reużywane — to maszyneria odkrywania wideo/YAML cinemon, nieistotna dla cymatic; review: scope.)
- **Error propagation:** Subprocess Blendera → `RuntimeError` ze stderr (wzorzec cinemon). Błędy walidacji audio propagują z `beatrix` (`NoAudioFileError`/`MultipleAudioFilesError`, komunikaty po polsku).
- **State lifecycle risks:** `.blend` z pętli MCP jest **efemeryczny** — nie commitować jako źródło; źródło = builder + params (INV2). `execute_blender_code` niesandboxowany → throwaway plik.
- **API surface parity:** Nowy CLI entry point (`cymatic-render`) — dodać do `pyproject.toml` `[project.scripts]`. Brak zmian w istniejących entry points.
- **Integration coverage:** Krytyczne ścieżki, których mocki nie udowodnią: (1) GN time-sampling na żywym Blenderze (Unit 2 spike + Unit 10); (2) render headless do mp4 (Unit 9, manualnie); (3) sync na 2 różnych sr (Unit 10).
- **Unchanged invariants:** `beatrix` (single source analizy) i config VSE `cinemon` pozostają nietknięte. Nowy pakiet czyta wyłącznie istniejący `*_analysis.json`.
- **Maintenance cost:** +1 pakiet (1 dev / 6 pakietów) — świadomy koszt (origin: opportunity cost, bet eksploracyjny obok luk cinemon issue #26). **Ścieżka utylizacji przy kill (review: product):** jeśli bet umrze (zbiorcza reguła go/no-go), `cymatic` usuwany z workspace members + sources, nie zostawiany jako orphan; kod buildera GN może być zarchiwizowany w `docs/solutions/` jeśli spike'y dały wiedzę.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| ~~GN time-sampling niesprawdzony (most B)~~ — **ROZWIĄZANE: Spike 2 PASS (2026-05-31)** na Blenderze 5.1.2, oba sr, err 6e-08 | Most B potwierdzony empirycznie; ryzyko zamknięte. Fallback-A pozostaje udokumentowany (`Sound_Nodes`), ale niepotrzebny dla rdzenia |
| **Sync rozjeżdża się na innym `sample_rate`** | `dt` z `times[]` per-track (NIE stała); Unit 10 mierzy na ≥2 sr (R3) — łapie regresję, której spike na 1 sr by nie wykrył |
| **MCP nie pokazuje ruchu** → sync nieweryfikowalny wizualnie | Sync z danych (Unit 10), nie z obrazu; MCP tylko do kompozycji (statyka) |
| ~~MCP/bridge nie działa w żywym Blenderze~~ — **ROZWIĄZANE: Spike 3a PASS (2026-05-31)** — oficjalny Blender Lab MCP, execute+screenshot zweryfikowane na 5.1.2 | Ryzyko zamknięte; socket loopback :9876, sandbox obecny |
| **Oba rdzeniowe bety padają** (Spike 2→A ORAZ 3a→ręczne) | **Zbiorcza reguła go/no-go: bet martwy, przerwać** — projekt zredukowałby się do ręcznego ślęczenia nad driverami |
| **`snap run blender` Linux-only** na macOS | `blender_executable` jawny w config; zachować gałąź snap dla Linux |
| **API GN 3.x vs 4.x** (`ng.inputs` usunięte) | Builder używa `node_group.interface.new_socket` (4.0+); test asercją; introspekcja node'ów przed budową |
| **Normalizacja nieczytelna** | Spike 1 z bramką kill przed buildem |
| **Niesandboxowany `execute_blender_code`** — blast radius szerszy niż 1 `.blend` (review: security): kod LLM ma dostęp do całego FS użytkownika (tokeny OAuth medusa, inne nagrania, `~`) | Proces MCP odpalany z `cwd` = izolowany katalog temp (NIE root nagrania); operować na **kopii** `.blend`, nie w katalogu nagrania; wywołania `execute_blender_code` w Unit 11 raczej szablonowane/recenzowane niż w pełni dowolne |
| **Socket loopback (port 9876)** — lokalna powierzchnia code-execution (review: security) | Bind tylko `127.0.0.1`; lifetime = sesja autoringu; jeśli `ahujasid/blender-mcp` — potwierdzić loopback-only (kryteria w Spike 3a) |
| **Koszt tokenów obrazu w pętli MCP** | `max_size` ~800px; trzymać najnowsze 1-2 screenshoty; ≤K iteracji + fallback (Unit 11) |

## Documentation / Operational Notes

- Po spike'ach: rozważyć `/ce:compound` → `docs/solutions/` (GN time-sampling, normalizacja per-track, pętla MCP) — brak istniejącej bazy wiedzy.
- **Zaktualizować `docs/DATA_FLOW_SPECIFICATION.md`** lub oznaczyć jego schemat JSON jako nieaktualny (pokazuje `spectral_analysis.*`, kod emituje flat `frequency_bands.*`).
- macOS: udokumentować ścieżkę `blender_executable` i wymaganą wersję Blendera (4.3+/4.5) w README pakietu.
- Render codec/container: dopasować do `packages/cinemon/blender_addon/vse/project_setup.py` (FFMPEG settings).

## Sources & References

- **Origin document:** [docs/brainstorms/2026-05-30-gn-audio-visualizer-requirements.md](docs/brainstorms/2026-05-30-gn-audio-visualizer-requirements.md)
- Kontrakt danych: `packages/beatrix/src/beatrix/core/audio_analyzer.py`
- Wybór audio: `packages/beatrix/src/beatrix/core/audio_validator.py`
- Wzorzec subprocess: `packages/cinemon/src/cinemon/project_manager.py`, `packages/cinemon/blender_addon/vse_script.py`
- Konsumpcja analizy: `packages/cinemon/blender_addon/vse/animation_compositor.py`
- Render FFMPEG: `packages/cinemon/blender_addon/vse/project_setup.py`
- Struktura katalogów: `packages/common/src/setka_common/file_structure/specialized/recording.py`
- Testy bez Blendera: `packages/cinemon/tests/conftest.py`
- External: `ahujasid/blender-mcp` (v1.5.6); Blender Manual GN (`Scene Time`, `Sample Index`, `Sample Curve`, `NodeTreeInterface` API 4.0+)
- Prior-art (study-only, gitignored): `research/prior-art/{Sound_Nodes,Audio-Offline-Analysis,Audio2Blender,blender-auto-render}/`
- **Dane testowe (gitignored, `research/audio/`):** CC0 jazz „Al McKibbon — Monsieur Phillipe" (archive.org, public domain), 120 s, dwa sr: `jazz_120s_48k.wav` (dt=0.010667) + `jazz_120s_44k.wav` (dt=0.011610) → `research/audio/analysis/*_analysis.json`. Reprodukują R3 (różny sr→różny dt) i skrajne skale pasm (bass 81.8 vs high 2.5). **Spike 1 PASS** na tych danych (kotwica p99).
```
