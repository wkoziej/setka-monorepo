---
date: 2026-06-02
topic: bitwig-mixed-audio-pipeline
---

# Bitwig jako etap miksu w pipelinie teledysku

## Problem Frame

Wojtas gra live, nagrywa w OBS (canvas → MKV) i — po pracach z
[[2026-05-31-midi-recording-orchestration-requirements]] — równolegle łapie wielościeżkowy
materiał w Bitwigu. Dziś pipeline teledysku (OBSession → Fermata → Beatrix → Cinemon → Blender)
analizuje i wkleja do klipu **surowe audio z OBS** — bez szansy na poprawę jakości.

Cel: wstawić **Bitwig jako ręczny etap post-produkcji audio** pomiędzy nagraniem a analizą.
Po nagraniu Wojtas wyrównuje głośności / miksuje w Bitwigu i dopiero **ten dopracowany eksport**
napędza analizę (Beatrix) oraz ścieżkę dźwiękową finalnego klipu. Głównym celem jest **jakość
post-produkcji audio**; targetowanie animacji per-ścieżka to bonus na później.

## Requirements

- **R1.** Struktura nagrania zyskuje **ustaloną konwencję katalogu** na eksport audio z Bitwiga
  (master mix; miejsce gotowe również na stemy per-instrument). Realizacja przez rozszerzenie
  `RecordingStructureManager` w `setka-common`.
- **R2.** **Beatrix analizuje master mix z Bitwiga** zamiast audio wyciągniętego z OBS —
  wskazaniem istniejącego CLI na plik w katalogu miksu (bez zmiany ducha Beatrix).
- **R3.** **Cinemon używa master miksu z Bitwiga jako finalnego audio klipu** (`--main-audio`
  wskazuje plik w katalogu miksu). Wideo nadal pochodzi z OBSession.
- **R4.** Różnica czasu audio↔wideo (dryf) jest kompensowana **ręcznie w montażu Blender**.
  Brak automatycznej synchronizacji w pipelinie; na start kompensację można pominąć.
- **R5.** Workflow jest **udokumentowany w wiki** (`Post-prod teledysk` + sekcja eksportu w
  `Bitwig Studio`, już uzupełniona), tak by ręczny krok miksu i konwencja handoffu były jasne.
- **R6. (bonus, odroczone)** Eksport stemów per-instrument umożliwia Beatrix per-stem i
  targetowanie animacji per-kamera w Cinemon. Pełna funkcja odroczona do drugiej fazy; **layout
  danych z R1 musi być gotowy na stemy bez przebudowy**.

## Success Criteria

- Ścieżka dźwiękowa finalnego klipu = **zmiksowany/wyrównany master z Bitwiga**, nie surowe
  audio z OBS.
- Beatrix uruchamia się na master miksie z Bitwiga, a jego zdarzenia napędzają Cinemon.
- Istnieje **powtarzalny, udokumentowany handoff**: eksport z Bitwiga → ustalony folder →
  istniejące CLI (Beatrix/Cinemon) → render.
- Dołożenie stemów w drugiej fazie **nie wymaga przebudowy** layoutu danych.

## Scope Boundaries

- **Bez** automatycznej synchronizacji audio/wideo i **bez** wyrównywania OBS-audio vs
  Bitwig-audio (dryf → ręcznie w Blenderze).
- **Bez** automatyzacji eksportu w Bitwigu (ręczne `File → Export Audio`) i **bez** generowania
  DAWproject.
- **Bez** pełnego targetowania per-stem teraz (R6 odroczone do drugiej fazy).
- **Bez** zmian w orkiestracji nagrywania — to domena
  [[2026-05-31-midi-recording-orchestration-requirements]].
- Sam miks pozostaje **ręczną pracą kreatywną**; automatyzujemy tylko handoff i przepięcie wejść.

## Key Decisions

- **Bitwig = ręczny etap miksu w pipelinie** (analogicznie do decyzji kreatywnych w Fermacie):
  cel to jakość audio, nie ground-truth z MIDI.
- **Master mix = kręgosłup** (finalne audio + Beatrix); **stemy = tani eksport** odblokowujący
  bonus per-track, ale kosztowny downstream → osobna faza.
- **Handoff = konwencja katalogu** w strukturze nagrania (minimum nowego kodu; Beatrix/Cinemon
  już przyjmują jawną ścieżkę audio) — zamiast kroku w Fermacie czy nowej komendy-glue.
- **Sync poza pipelinem** — dryf koryguje człowiek w Blenderze; ewentualny pojedynczy parametr
  offsetu w Cinemon to przyszłość, nie MVP.

## Dependencies / Assumptions

- Bitwig produkuje **zmiksowany master** (i opcjonalnie stemy) — zależy od wielościeżkowego
  capture z [[2026-05-31-midi-recording-orchestration-requirements]] (lub przynajmniej miksu
  stereo nagranego w Bitwigu).
- **Potwierdzone:** Bitwig eksportuje dowolny track osobno oraz `Project Master` przez
  `File → Export Audio` (wiki `Bitwig Studio` zaktualizowane, źródło: Bitwig Userguide).
- Beatrix (CLI: ścieżka audio + katalog wyjścia) i Cinemon (`--main-audio`) **już przyjmują
  jawną ścieżkę** → do weryfikacji w planowaniu, że nie trzeba zmian w kodzie tych pakietów.
- `RecordingStructureManager` (`setka-common`) to wspólne miejsce na nowy katalog.

## Outstanding Questions

### Deferred to Planning

- [Affects R1][Technical] Nazwa i kształt konwencji katalogu (`mixed/` vs `bitwig/`), nazewnictwo
  pliku master vs stemów, akceptowane formaty (WAV/FLAC) i API w `RecordingStructureManager`.
- [Affects R2][Technical] Czy Beatrix/Cinemon wymagają jakiejkolwiek zmiany kodu, czy wystarczy
  wskazanie nowej ścieżki (zweryfikować na realnym CLI).
- [Affects R3/R4][Technical] Rola audio z OBS po zmianie (przestajemy je ekstraktować czy
  zostaje nieszkodliwym fallbackiem) oraz ewentualny pojedynczy parametr offsetu audio w Cinemon.
- [Affects R6][Needs research] Projekt drugiej fazy: Beatrix per-stem (wiele wejść →
  per-stem events) i mapowanie stem→kamera/strip w Cinemon.
- [Drobne][Technical] Wiki: poprawić lokalizację paternologii (`~/dev/paternologia` →
  `packages/paternologia` po PR #30) na stronie `Paternologia` i w workflowach.

## Next Steps

→ `/ce:plan` — wszystkie decyzje produktowe rozstrzygnięte; pozostałe pytania są techniczne
i należą do planowania.
