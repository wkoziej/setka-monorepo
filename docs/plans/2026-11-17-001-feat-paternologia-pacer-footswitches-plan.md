---
title: "feat(paternologia): obsługa zewnętrznych footswitchy Pacera (FS1–FS4)"
type: feat
status: active
date: 2026-11-17
---

# feat(paternologia): obsługa zewnętrznych footswitchy Pacera (FS1–FS4)

## Overview

Paternologia programuje tylko 6 stompswitchy Pacera (SW1–SW6). Użytkownik podłącza podwójny momentary footswitch Ampero do gniazda Pacera opisanego „FS 1/3”. Daje to 2 dodatkowe przyciski. Plan dodaje do utworu sekcję footswitchy, którą edytujemy w UI, zapisujemy w YAML i eksportujemy do `.syx` tak samo jak przyciski SW.

## Problem Frame

Na żywo brakuje przycisków: 6 SW nie wystarcza dla niektórych utworów. Pacer ma wejścia na zewnętrzne footswitche (kontrolki FS1–FS4). Te kontrolki mają taki sam format kroków (step) jak SW, ale nie mają LED. Teraz eksport ich nie dotyka, więc ich konfiguracja w presecie jest przypadkowa (zostaje z poprzedniej zawartości presetu).

## Requirements Trace

- R1. Utwór może mieć akcje dla footswitchy FS1–FS4 (do 6 akcji na footswitch, te same typy akcji co dla SW).
- R2. Eksport `.syx` programuje kontrolki FS. Nieużywane FS są czyszczone, więc YAML w pełni określa stan presetu (ta sama zasada co dla SW i M CFG).
- R3. Edycja footswitchy w formularzu utworu, widok utworu i widok live pokazują footswitche.
- R4. Akcje footswitchy biorą udział w indeksie MIDI (wykrywanie utworu na żywo) i w indeksie użycia presetów — tak samo jak akcje SW.
- R5. Obecne pliki YAML utworów ładują się bez zmian (brak sekcji = brak footswitchy).

## Scope Boundaries

- Nie zmieniamy ustawień globalnych Pacera (`TARGET_GLOBAL`). Tryb gniazda FS (footswitch vs expression) użytkownik ustawia ręcznie na urządzeniu. Krytyczne: nigdy `TARGET_GLOBAL + elm=0x1E`.
- Bez pedałów ekspresji (EXP1/EXP2) i bez stompswitchy A–D.
- Bez trybów innych niż „all steps in one shot” (mode=0), tak jak dla SW.
- Bez konfiguracji LED dla FS (FS nie mają LED).

## Context & Research

### Relevant Code and Patterns

- `packages/paternologia/src/paternologia/models.py` — `PacerButton`, `Song.pacer` (`max_length=6`), `Song.on_load`.
- `packages/paternologia/src/paternologia/pacer/constants.py` — `STOMPSWITCHES` (0x0D–0x12).
- `packages/paternologia/src/paternologia/pacer/export.py` — pętla SW: control mode → 6 kroków (czyszczenie `MSG_CTRL_OFF`) → 6 ramek LED.
- `packages/paternologia/src/paternologia/routers/songs.py` — `_build_song_from_form`, `_parse_action(prefix)`, `get_action_row(context="on_load")`. Sekcja `on_load` to gotowy wzorzec drugiej listy akcji z własnym prefiksem pól.
- `packages/paternologia/templates/partials/action_row.html` i `action_fields.html` — `field_prefix` zależy od `action_context`.
- `packages/paternologia/templates/song_edit.html`, `song.html`, `partials/live_song.html`, `partials/song_card.html`, `partials/pacer_button.html`.
- `packages/paternologia/src/paternologia/midi/index.py` (`SongMidiIndex.build`) i `src/paternologia/usage.py` (`PresetUsageIndex.build`) — iterują `song.pacer`.
- `packages/paternologia/src/paternologia/pacer/readback.py` — `missing_frames` porównuje wysłane ramki z dumpem presetu.
- `packages/paternologia/src/paternologia/storage.py` — zapis przez `model_dump(mode="json")`.

### Protokół Pacera

- pacer-editor `src/pacer/constants.js`: `CONTROL_FOOTSWITCH_1..4 = 0x18..0x1B` (repo `~/dev/paternologia/workspace/pacer_programming/pacer-editor`).
- Gniazdo „FS 1/3”: podwójny przełącznik TRS daje dwa sygnały. Zakładamy tip → FS1 (0x18), ring → FS3 (0x1A). Sprawdzamy na sprzęcie (patrz Deferred).

### Institutional Learnings

- Brak wpisów w `docs/solutions/` o Pacerze. Poprzedni plan `docs/plans/2026-11-07-001-feat-paternologia-pacer-preset-load-messages-plan.md` (M CFG) ustalił zasadę „zawsze wysyłaj wszystkie wpisy, nieużywane czyść”.

## Key Technical Decisions

- **Osobne pole `Song.footswitches`, nie rozszerzenie `Song.pacer` do 10:** pozycja na liście `pacer` = numer SW i UI pozwala przesuwać przyciski. FS mają stałe numery fizyczne (FS1, FS3), więc pozycja nie może być numerem. Osobne pole nie zmienia semantyki istniejących danych.
- **Lista elementów z polem `fs` (1–4), nie słownik `{1: ...}`:** zapis idzie przez `model_dump(mode="json")`. JSON zmienia klucze int na string, więc słownik z kluczami int psuje round-trip. Lista z jawnym `fs` jest jednoznaczna w YAML. Walidacja: `fs` w 1–4, unikalne, maks. 4 elementy.
- **Model obsługuje FS1–FS4, a nie tylko FS1/FS3:** koszt jest ten sam (stała mapa 4 ID). Inne podłączenie (np. drugie gniazdo) nie wymaga zmiany kodu.
- **Eksport zawsze programuje wszystkie 4 FS (puste = wyczyszczone):** ta sama zasada co SW i M CFG. Stary śmieć w presecie nie odpala się z footswitcha.
- **Brak ramek LED dla FS:** FS nie mają LED. Wspólną logikę kroków (mode + 6 kroków) wydzielamy do funkcji pomocniczej używanej przez SW i FS (DRY). LED zostaje tylko w gałęzi SW.
- **UI: 4 stałe sloty FS1–FS4 w formularzu edycji (slot bez nazwy i bez akcji = nieużywany; akcje bez nazwy → nazwa `FS{n}`, żeby nie zniknęły po cichu):** bez przesuwania i dodawania. Sloty mają stały numer, więc nie potrzeba JS do renumeracji. Pola formularza: `fs_{n}_name`, `fs_{n}_action_{i}_*`. W widoku utworu i live pokazujemy tylko używane FS.
- **Kontekst akcji `footswitch` w partialach akcji:** rozszerzamy istniejący mechanizm `action_context` (dziś `on_load`). Nie tworzymy kopii partiali.

## Open Questions

### Resolved During Planning

- Gniazdo: „FS 1/3” (odpowiedź użytkownika) → kontrolki FS1 i FS3.
- Format YAML: lista z polem `fs` (z powodu `model_dump(mode="json")`).

### Deferred to Implementation

- **Mapowanie tip/ring → FS1/FS3:** sprawdzić na sprzęcie (naciśnięcie każdego przycisku Ampero i obserwacja MIDI). Jeśli jest odwrotnie, to tylko kwestia nazwy slotu w YAML — kod się nie zmienia.
- **Ustawienie globalne gniazda FS w Pacerze:** może trzeba ręcznie przełączyć wejście w tryb footswitch (menu Setup na urządzeniu). Nie robimy tego przez SysEx.
- **Czy dump presetu (`CONTROL_ALL`) zwraca ramki FS w tym samym formacie co wysłane:** jeśli nie, `missing_frames` zgłosi fałszywe braki. Sprawdzić przez „Wyślij do Pacera” + read-back. Jeśli format jest inny, odfiltrować FS w porównaniu albo dopasować format — decyzja po zobaczeniu dumpu.
- **Polaryzacja przełącznika Ampero:** jeśli Pacer odpala akcję przy puszczeniu zamiast przy naciśnięciu, trzeba sprawdzić, czy Pacer wykrywa polaryzację przy starcie (podłączenie przed włączeniem).

## Implementation Units

- [x] **Unit 1: Model danych footswitchy**

**Goal:** `Song` przyjmuje opcjonalną listę footswitchy z numerem `fs`.

**Requirements:** R1, R5

**Dependencies:** brak

**Files:**
- Modify: `packages/paternologia/src/paternologia/models.py`
- Test: `packages/paternologia/tests/test_models.py`, `packages/paternologia/tests/test_storage.py`

**Approach:**
- Nowy model footswitcha = `PacerButton` + pole `fs` (int 1–4). Dziedziczy nazwę i do 6 akcji.
- `Song.footswitches`: lista, domyślnie pusta, maks. 4, walidator unikalności `fs`.

**Execution note:** test-first.

**Patterns to follow:** `PacerButton`, walidatory w `models.py` (np. `preset_cc`).

**Test scenarios:**
- Happy path: utwór z FS1 i FS3 (po 1 akcji) waliduje się poprawnie.
- Happy path: utwór bez klucza `footswitches` → pusta lista (R5).
- Error path: `fs=0` i `fs=5` → błąd walidacji.
- Error path: dwa wpisy z `fs=1` → błąd walidacji.
- Error path: footswitch z 7 akcjami → błąd walidacji.
- Integration: zapis i odczyt przez `Storage` (round-trip YAML) zachowuje `fs` i akcje.

**Verification:** testy modelu i storage są zielone; istniejące pliki `data/songs/*.yaml` ładują się bez błędów.

- [x] **Unit 2: Eksport `.syx` dla FS1–FS4**

**Goal:** eksport programuje kontrolki 0x18–0x1B. Nieużywane są czyszczone. Bez LED.

**Requirements:** R2

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/paternologia/src/paternologia/pacer/constants.py`, `packages/paternologia/src/paternologia/pacer/export.py`
- Test: `packages/paternologia/tests/test_pacer_export.py`

**Approach:**
- Stała `FOOTSWITCHES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}` ze źródłem (pacer-editor) w komentarzu.
- Wydzielić z pętli SW funkcję „mode + 6 kroków dla kontrolki” i użyć jej dla SW i FS. LED zostaje tylko w SW.
- Kolejność ramek: nazwa → SW1–SW6 → FS1–FS4 → M CFG.

**Execution note:** test-first. Najpierw test charakteryzujący: bajty eksportu dla utworu bez footswitchy nie zmieniają się poza dopisanymi ramkami FS (ochrona przy refaktorze pętli SW).

**Patterns to follow:** obecna pętla SW w `export.py`; testy w `test_pacer_export.py`.

**Test scenarios:**
- Happy path: FS1 z akcją CC → ramka kroku 1 dla control_id 0x18 z właściwym kanałem i danymi; kroki 2–6 wyczyszczone.
- Happy path: FS3 z akcją PRESET dla GP-50 → CC0 (reguła `preset_cc` działa też dla FS).
- Edge case: utwór bez footswitchy → wszystkie 4 FS mają ramkę mode + 6 wyczyszczonych kroków.
- Edge case: brak jakiejkolwiek ramki LED dla 0x18–0x1B.
- Integration: ramki SW dla istniejącego utworu (np. z `data/songs`) są identyczne jak przed refaktorem.

**Verification:** testy eksportu są zielone; dla każdego FS jest dokładnie 7 ramek (1 mode + 6 kroków).

- [x] **Unit 3: Formularz edycji i endpointy HTMX**

**Goal:** edycja FS1–FS4 w formularzu utworu i zapis do modelu.

**Requirements:** R1, R3

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/paternologia/src/paternologia/routers/songs.py`, `packages/paternologia/templates/song_edit.html`, `packages/paternologia/templates/partials/action_row.html`, `packages/paternologia/templates/partials/action_fields.html`
- Create: `packages/paternologia/templates/partials/footswitch_card.html`
- Test: `packages/paternologia/tests/test_api.py`

**Approach:**
- Nowa sekcja „Footswitche” pod przyciskami PACER: 4 stałe karty FS1–FS4 z polem nazwy i listą akcji. Podpowiedź: gniazdo FS 1/3 → FS1 i FS3.
- `_build_song_from_form`: dla n=1..4 czytaj `fs_{n}_name`. Slot bez nazwy i akcji pominięty; akcje bez nazwy dostają nazwę `FS{n}`. Akcje przez istniejące `_parse_action` z prefiksem `fs_{n}_action_{i}`.
- Endpointy `action-row`, `action-types`, `action-fields`: dodać `context="footswitch"`. Numer FS przekazujemy w istniejącym `button_idx`. Partiale budują `field_prefix` dla tego kontekstu.

**Patterns to follow:** sekcja `on_load` (regex na indeksy, `action_context`).

**Test scenarios:**
- Happy path: POST formularza z `fs_1_name` i jedną akcją → zapisany utwór ma FS1 z tą akcją.
- Happy path: POST z FS1 i FS3, bez FS2 → zapisane dwa wpisy z `fs` 1 i 3.
- Edge case: slot z akcją, ale bez nazwy → slot pominięty (zgodnie z obecnym zachowaniem przycisków SW).
- Edge case: usunięty środkowy wiersz akcji (luka w indeksach) → pozostałe akcje zapisane po kolei.
- Integration: GET edycji utworu z FS3 → formularz ma wypełnioną kartę FS3.
- Integration: `GET /partials/action-row?context=footswitch&button_idx=3&action_idx=0` → pola z prefiksem `fs_3_action_0_`.

**Verification:** testy API są zielone; ręcznie: edycja → zapis → ponowna edycja pokazuje te same dane.

- [x] **Unit 4: Widoki utworu, live i karta utworu**

**Goal:** pokazać używane footswitche w widoku utworu i w widoku live.

**Requirements:** R3

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/paternologia/templates/song.html`, `packages/paternologia/templates/partials/live_song.html`, `packages/paternologia/templates/partials/song_card.html`
- Test: `packages/paternologia/tests/test_api.py`, `packages/paternologia/tests/test_live_api.py`

**Approach:** pod siatką SW dodać rząd z kartami „FS1 …”, „FS3 …” (ten sam partial `action_summary.html`). Brak footswitchy = brak rzędu. Karta utworu: licznik FS obok licznika przycisków.

**Test scenarios:**
- Happy path: widok utworu z FS3 zawiera etykietę „FS3” i nazwę.
- Happy path: widok live z FS1 zawiera jego akcje.
- Edge case: utwór bez footswitchy → brak sekcji FS w HTML.

**Verification:** testy zielone; ręcznie: widok live na kiosku (lubudu) mieści rząd FS bez przewijania w poziomie.

- [x] **Unit 5: Indeks MIDI i indeks użycia presetów**

**Goal:** akcje FS liczą się tak samo jak akcje SW.

**Requirements:** R4

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/paternologia/src/paternologia/models.py` (pomocnicza metoda/właściwość `Song`, która zwraca wszystkie przyciski SW + FS), `packages/paternologia/src/paternologia/midi/index.py`, `packages/paternologia/src/paternologia/usage.py`
- Test: `packages/paternologia/tests/test_midi_index.py`, `packages/paternologia/tests/test_usage.py`

**Approach:** jedno miejsce w `Song`, które zwraca przyciski SW i FS. Oba indeksy używają go zamiast `song.pacer` (DRY).

**Test scenarios:**
- Happy path: utwór z akcją PRESET tylko na FS1 → `SongMidiIndex` mapuje (kanał, program) na ten utwór.
- Happy path: preset użyty tylko na FS3 → pojawia się w `PresetUsageIndex`.
- Edge case: ten sam preset na SW i FS w jednym utworze → utwór wymieniony raz.

**Verification:** testy indeksów są zielone.

- [ ] **Unit 6: Weryfikacja na sprzęcie i dokumentacja** *(dokumentacja zrobiona; weryfikacja na sprzęcie czeka)*

**Goal:** potwierdzić działanie na Pacerze i opisać format.

**Requirements:** R2, R3

**Dependencies:** Units 1–5

**Files:**
- Modify: `packages/paternologia/SPEC.md` (format `footswitches` w YAML), `packages/paternologia/README.md` (podłączenie Ampero do gniazda FS 1/3)
- Test: `packages/paternologia/tests/test_pacer_readback.py` (tylko jeśli dump FS ma inny format — patrz Deferred)

**Approach:**
- Utwór testowy z FS1 = CC i FS3 = nuta na M:S. Eksport, wysyłka z `--sysex-interval=20`, read-back.
- Sprawdzić: (a) tip/ring → FS1/FS3, (b) read-back nie zgłasza braków, (c) akcje odpalają się przy naciśnięciu, (d) SW1–SW6 działają bez zmian.

**Verification:** oba przyciski Ampero wysyłają oczekiwane MIDI; read-back bez błędów; dokumentacja opisuje format i podłączenie.

## System-Wide Impact

- **Interaction graph:** eksport (`routers/pacer.py` → `export_song_to_syx`), read-back, indeks MIDI w listenerze live, indeks użycia presetów, formularz utworu.
- **Error propagation:** błędy walidacji FS idą istniejącą ścieżką `_format_validation_error` (HTTP 422 z komunikatem).
- **State lifecycle risks:** eksport rośnie o 28 ramek SysEx (4 × 7). Przy `--sysex-interval=20` to ok. 0,6 s więcej na wysyłkę. Cache YAML w `Storage` nie wymaga zmian (parsuje cały model).
- **API surface parity:** plik `.syx` do pobrania i „Wyślij do Pacera” używają tej samej funkcji eksportu.
- **Integration coverage:** tylko test na sprzęcie (Unit 6) potwierdza mapowanie gniazda i format dumpu.

## Risks & Dependencies

- **Read-back może zgłaszać fałszywe braki dla FS:** mitygacja w Unit 6 (sprawdzić dump, dopasować porównanie).
- **Refaktor pętli SW może zmienić bajty SW:** mitygacja — test charakteryzujący w Unit 2 przed refaktorem.
- **Ustawienia globalne Pacera:** poza zakresem SysEx; tylko ręczna konfiguracja i opis w README. Nie wysyłamy nic do `TARGET_GLOBAL`.

## Documentation / Operational Notes

- Kiosk lubudu robi auto-deploy z `master` — po merge zmiana trafi na kiosk w ciągu ok. 2 min. Sprawdzić widok live na małym ekranie.
- Po wdrożeniu trzeba ponownie wysłać presety utworów, które mają używać footswitchy.

## Sources & References

- pacer-editor: `src/pacer/constants.js` (`CONTROL_FOOTSWITCH_1..4`)
- Related plan: `docs/plans/2026-11-07-001-feat-paternologia-pacer-preset-load-messages-plan.md`
- Related code: `packages/paternologia/src/paternologia/pacer/export.py`, `packages/paternologia/src/paternologia/routers/songs.py`
