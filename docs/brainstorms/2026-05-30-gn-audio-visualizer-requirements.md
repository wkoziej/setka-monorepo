# Wymagania: Wizualizer audio 3D (Geometry Nodes + Blender MCP)

- **Data:** 2026-05-30
- **Status:** Wymagania — gotowe do planowania (`/ce:plan`)
- **Autorzy:** Wojciech Koziej + Claude
- **Powiązane pakiety:** `beatrix` (źródło danych), `cinemon` (referencja architektury), `setka-common` (struktura plików)

## Problem i cel

Dane z `beatrix` (beaty, onsety, energy_peaks, sekcje oraz time-series energii pasm bass/mid/high) są dziś konsumowane wyłącznie przez `cinemon` w trybie **VSE** — animacje 2D na paskach wideo (skala, shake, kolor). Nie istnieje ścieżka generująca **proceduralną wizualizację 3D** sterowaną tą analizą.

**Cel:** Dla wybranej ścieżki dźwiękowej wygenerować abstrakcyjny wizualizer 3D (scena Geometry Nodes), sterowany danymi `beatrix`, renderowany do pliku wideo. Budowa sceny prowadzona iteracyjnie przez Claude'a za pośrednictwem **Blender MCP** (pętla: zbuduj → screenshot viewportu → oceń → popraw).

## Użytkownik i wartość

- **Użytkownik:** twórca nagrań (Wojciech) — chce z istniejącej analizy audio uzyskać wizualnie atrakcyjny materiał 3D bez ręcznego ślęczenia w Blenderze nad driverami.
- **Wartość:** nowy typ outputu z tego samego pipeline'u (OBS → beatrix → render), reużycie analizy jako jedynego źródła prawdy, autoring sceny przez agenta zamiast ręcznej pracy node-by-node.

## Decyzje (rozstrzygnięte w tym brainstormie)

1. **Rezultat:** abstrakcyjny wizualizer renderowany do **pliku wideo** (mp4). Nie łączymy go (na razie) z footage z OBS.
2. **Rola MCP — HIPOTEZA DO WALIDACJI, nie decyzja zamknięta.** Zamierzenie: iteracyjny dialog wizualny (Claude buduje scenę przez MCP, ocenia, poprawia). MCP = partner autoringu, nie runtime renderu. **Dwa tryby oceny, bo różnią się tym co mierzą:**
   - **statyczny screenshot viewportu** → kompozycja/struktura sceny (NIE pokaże synchronizacji — sync to własność ruchu);
   - **krótki render-klip / playback** → synchronizacja akcentów z beatami (jedyny sposób na weryfikację sync).
   - **Wymaga spike'a (patrz „Ryzyka i spike'i")** zanim uznamy tryb autoringu za przyjęty. **Fallback:** jeśli pętla nie zbiega w budżecie iteracji — agent generuje setup GN raz, człowiek dostraja ręcznie (lub podejście A).
3. **Mapowanie audio→obraz:** **hybryda** — time-series pasm (bass/mid/high) steruje ciągłym ruchem/formą tła; beaty i `energy_peaks` dorzucają dyskretne akcenty (impulsy, błyski, wyrzuty cząstek).
4. **Most danych beatrix→GN: podejście B — „mesh-jako-dane".** Cała analiza kodowana jest jako geometria danych (krzywa/siatka: X = czas, atrybuty wierzchołków = bass/mid/high + flagi beat/peak). Drzewo GN **próbkuje** ten obiekt po aktualnej klatce i czyta wszystkie cechy naraz.
   - **Realna oś B-vs-A:** B trzyma całą piosenkę jako **jeden zapytywalny obiekt** (brak N kanałów driverów); A jest mechanicznie prostsze i to znany wzorzec. *Uwaga:* „poprawność przy scrubbingu" **nie** różnicuje B od A — keyframe scrubują poprawnie z definicji; to nie jest argument za B.
   - **Ryzyko:** time-sampling atrybutów po czasie w GN jest niesprawdzony (otwarte pytanie 3, spike). Gdyby B okazało się trudne, A pozostaje gotowym wzorcem awaryjnym.
   - **Odrzucone:** podejście C (natywny „Bake Sound to F-Curve") — dubluje analizę, tworzy drugie źródło prawdy, ryzyko rozjazdu timingu.
5. **Normalizacja pasm — w zakresie nowego modułu (nie beatrix).** `bass/mid/high_energy` to surowe magnitudy STFT (`np.mean(np.abs(stft))`): nieznormalizowane, różne skale per pasmo, zmienne per utwór. Nowy moduł liczy **deterministyczny** transform 0..1 raz na całą analizę. **Cel na MVP = czytelność W OBRĘBIE utworu** (per-track percentyl/max) — NIE porównywalność między utworami; te dwa cele są sprzeczne (per-track normalizacja kasuje właśnie różnice głośności między utworami). Porównywalność między utworami (skala absolutna/log kalibrowana raz) = późniejsze rozszerzenie, poza MVP. beatrix pozostaje nietknięty (single source).

## Zakres (in scope)

- Odczyt istniejącego `*_analysis.json` z `beatrix`. **MVP konsumuje:** `duration`, `sample_rate`, `tempo.bpm`, `animation_events.{beats,onsets,energy_peaks}`, `frequency_bands.{times,bass_energy,mid_energy,high_energy}`. **`animation_events.sections` POMINIĘTE na MVP** (to listy dictów `{start,end,label}`, nie skalary — kodowanie odłożone; hybryda i kryterium 1 ich nie wymagają).
- **Normalizacja pasm** do zakresu wizualnego (Decyzja 5) — warunek widoczności ciągłej energii. *Spike-gated:* wchodzi do MVP pod warunkiem pozytywnego wyniku Spike 1.
- Konwersja analizy na obiekt-danych w scenie 3D (most B). *Spike-gated:* pod warunkiem Spike 2; przy kill → fallback do podejścia A (keyframe+drivery).
- Co najmniej jeden działający preset wizualny (hybryda ciągłe+impulsy) jako pierwszy „pionowy plasterek". **Parametry presetu na MVP = prosty dataclass/dict** przekazywany do skryptu Blendera (NIE system YAML z `cinemon` — przedwczesny dla jednego presetu). Preset wystawia kilka wpływowych parametrów (paleta, prymityw geometrii, intensywność akcentów), by tanio próbkować warianty.
- **Spike MCP** (prerequisite, patrz „Ryzyka"): potwierdzić wybrany serwer MCP umie uruchomić Pythona w żywym Blenderze i pobrać screenshot viewportu. Bez tego pętla autoringu jest nieweryfikowalna.
- Autoring sceny przez Blender MCP z pętlą (zależny od wyniku spike'a).
- Render do pliku wideo zgodny ze strukturą katalogów (`blender/render/`).
- Zgodność z czasem: synchronizacja klatka↔sekunda wg `fps` i `beatrix` (czas w sekundach).
- Wybór ścieżki audio przez reużycie `beatrix.core.audio_validator.AudioValidator` (publiczna klasa, `cinemon` już importuje z `beatrix` — bez nowego kodu analizy).

## Poza zakresem (non-goals)

- Łączenie warstwy 3D z footage z OBS (osobny, późniejszy pomysł).
- Własna analiza audio w tym module — **wszystkie** dane pochodzą z `beatrix`.
- Render produkcyjny przez MCP (render leci osobno, headless).
- Biblioteka wielu gotowych presetów na start (MVP = jeden dobry preset; kolejne to rozszerzenie).
- Real-time playback dla widza końcowego (samodzielny odtwarzacz). Podgląd w edytorze przez screenshoty MCP **jest** w zakresie.

## Kryteria sukcesu

**MVP (gate „gotowe"):**
1. Z istniejącego `*_analysis.json` powstaje scena 3D, w której widać reakcję na: (a) ciągłą **znormalizowaną** energię pasm i (b) dyskretne beaty/peaki.
2. Sync **obiektywnie**: akcenty wizualne padają w granicach **±N klatek** (N do ustalenia, np. ≤2) od timestampów beatów/peaków z beatrix — mierzalne z danych, nie tylko „na oko + ucho".
3. Próbkowanie po czasie działa poprawnie: dla dowolnej klatki stan wizualizacji odpowiada danym beatrix w tym czasie (test poprawności implementacji samplingu — nie dowód wyższości B nad A). *Mierzone na ≥2 utworach o RÓŻNYM `sample_rate`* (siatka STFT zależna od sr — patrz Otwarte 3).
4. **Stop-rule:** twórca akceptuje co najmniej jeden wyrenderowany klip jako warty użycia, **w budżecie ≤K iteracji pętli/dostrojeń** (K do ustalenia, np. 5); brak akceptacji po K → fail gate i fallback (generuj-raz + ręczne). Warunek zakończenia, nie „rób ładniej" w nieskończoność.

**Faza 2 (poza gate MVP, zależne od spike'a):**
5. Pętla MCP autoringu zbiega bez ręcznej ingerencji w node'y w budżecie iteracji — przeniesione tu, bo zależy od nierozstrzygniętej infrastruktury MCP (otwarte pytanie 2).

> Uwaga: „beatrix = jedyne źródło analizy" to ograniczenie architektoniczne (Decyzja 4), nie kryterium-wynik — usunięte z listy kryteriów, by lista mierzyła rezultaty, nie inwarianty.

## Otwarte pytania (do planowania)

1. **Gdzie żyje kod?** Nowy pakiet vs. rozszerzenie `cinemon` — **decyzja do jawnego ważenia, nie domyślnego nowego pakietu.** Wspólne z cinemon: kontrakt danych beatrix, subprocess Blendera (`project_manager.py`), wzorzec presetów, `audio_validator`. Tyle wspólnej maszynerii sugeruje **wspólny core lub submode w cinemon** zamiast czystego splitu — zwłaszcza przy 1 deweloperze / 6 pakietach (koszt utrzymania). Paradygmat-specyficzne (autoring GN, pętla MCP, render 3D) vs wspólne — rozpisać w `/ce:plan` i zdecydować kosztem utrzymania, nie nowością.
2. **Setup Blender MCP** — który konkretny serwer (np. `ahujasid/blender-mcp`?), czy umie Python + screenshot viewportu w docelowym Blenderze, kroki integracji. **Prerequisite-spike, nie część buildu wizualizera.**
3. **Mechanika próbkowania po czasie w GN** — krzywa vs siatka; matematyka time→index (`time_sec = frame / fps`). **UWAGA: siatka czasu jest zależna od utworu** — beatrix ładuje audio z `sr=None`, więc krok `frequency_bands.times` = `hop_length/sr` jest różny per plik (~23ms przy 22050 Hz, ~10.7ms przy 48 kHz). Most B MUSI czytać `sample_rate` i wyprowadzać index z faktycznego `times[]`, nie z zakładanego stałego kroku — inaczej sync rozjedzie się na utworach o innym sr (przejdzie spike na jednym, pęknie na produkcji). `sections` pominięte na MVP (patrz Zakres).
4. **Konfiguracja** — kiedy/czy migrować z dataclass MVP do wzorca YAML `cinemon` (próg: pojawienie się drugiego presetu).
5. **Reproducible artifact — rozstrzygnięte:** źródłem prawdy jest **skrypt-builder GN (Python) + dataclass parametrów presetu**, commitowany do repo. `.blend` wytworzony interaktywnie przez pętlę MCP = produkt uboczny eksploracji, NIE źródło renderu. Determinizm: `builder + preset-params + analysis.json` → ten sam render. (Otwarte: dokładny kształt serializacji parametrów — implementacja.)

## Ryzyka i spike'i (przed lockiem zakresu)

Trzy techniczne ryzyka rdzenia są realnie niesprawdzone — każde dostaje spike z warunkiem kill/continue **przed** pełnym buildem:

1. **Normalizacja pasm** — czy deterministyczny per-track transform 0..1 daje wizualnie czytelny ruch W OBRĘBIE utworu (porównywalność między utworami świadomie poza MVP). (Decyzja 5)
2. **GN time-sampling** — czy drzewo GN potrafi czytać atrybut po czasie (Sample Index/Nearest/Curve) z poprawnym `time→index`, wydajnie przy tysiącach wierzchołków. Kill → fallback do podejścia A. (Otwarte 3)
3. **Pętla MCP** — rozbita na dwa rozłączne warunki (drugi nie jest binarny):
   - **3a (binarny, decydowalny w godziny):** czy wybrany serwer MCP umie Python+screenshot w żywym Blenderze. Kill → fallback: generacja raz + ręczne dostrojenie.
   - **3b (hipoteza Fazy 2, NIE warunek kill spike'a):** czy ocena z screenshotu realnie zbiega scenę w ≤K iteracji wg konkretnej rubryki kompozycji. Bez progu nie jest warunkiem kill — przeniesione do Fazy 2 (kryterium 5).
   (Decyzja 2, Otwarte 2)

**Zbiorcza reguła go/no-go:** fallbacki są per-ryzyko, ale jeśli **jednocześnie** Spike 2 → fallback-A (ręczne drivery) ORAZ Spike 3a/3b → fallback-ręczny, to projekt redukuje się do ręcznego ślęczenia w Blenderze nad driverami — czyli dokładnie tego, co miał wyeliminować (patrz „Użytkownik i wartość"). W tym scenariuszu **bet jest martwy — przerwać, nie kontynuować**.

**Opportunity cost:** to drugi konsument beatrix→wideo obok cinemon, który ma własne luki (jitter/continuous — issue #26, brakujące presety). Bet uznany za **eksploracyjny** — świadomy wybór nowości nad domknięciem cinemon.

## Referencje (repo-relative)

- Schemat danych: `packages/beatrix/src/beatrix/core/audio_analyzer.py`
- CLI / zapis JSON: `packages/beatrix/src/beatrix/cli/analyze_audio.py`
- Wzorzec wykonania Blendera: `packages/cinemon/src/cinemon/project_manager.py`
- Wzorzec konsumpcji analizy + YAML: `packages/cinemon/blender_addon/vse/animation_compositor.py`
- Struktura katalogów: `setka-common.file_structure.specialized.RecordingStructureManager`
