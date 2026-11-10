---
title: "feat: Switch A Pacera w eksporcie + jednonutowy toggle nagrywania"
type: feat
status: planned
date: 2026-09-10
origin: music-box-wiki `wiki/devices/Pacer.md`, `wiki/connections/MIDI routing — main rig.md`
---

# feat: Switch A Pacera w eksporcie + jednonutowy toggle nagrywania

## Overview

Dwie niezależne, ale sąsiadujące zmiany w `paternologia`:

1. **Eksport SysEx obejmuje switch A Pacera** (control ID `0x14`), a nie tylko
   SW 1–6 (`0x0D`–`0x12`). Pojemność konfiguracji per utwór rośnie z **36 do 42
   slotów** (7 kontrolerów × 6 kroków) bez żadnego zakupu sprzętu.
2. **Nagrywanie da się włączyć i wyłączyć jedną nutą z dowolnego kroku utworu**,
   bez wchodzenia w read-only preset Transport Pacera. Dziś wymaga to dwóch
   naciśnięć i przełączenia całego kontrolera w tryb modalny.

Zmiany są **wyłącznie addytywne**. Istniejąca ścieżka nagrywania (switch B →
preset Transport → MCU Play/Stop → nuty 94/93) pozostaje nietknięta i działająca.

## Problem Frame

### 1.1 Cztery górne switche leżą odłogiem

Pacer ma **10 programowalnych footswitchy** (SW 1–6 oraz A–D) plus 4 gniazda
na externale. `pacer/constants.py` zna **sześć**:

```python
STOMPSWITCHES = {i: 0x0D + i for i in range(6)}  # SW1-SW6
```

`pacer/export.py:34` iteruje `for btn_idx in range(6)`. Switche A–D
(`0x14`–`0x17`) nie są w ogóle adresowane — nie są ani programowane, ani
czyszczone. Zachowują fabryczne przypisania.

Pełna tabela control ID (źródło: `pacer-editor/src/pacer/constants.js`, ten sam,
na którym oparty jest nasz `constants.py`):

| Kontroler | Control ID |
|---|---|
| Preset Name | `0x01` |
| SW 1–6 | `0x0D`–`0x12` |
| RESERVED | `0x13` |
| **SW A–D** | **`0x14`–`0x17`** |
| FS 1–4 (externale) | `0x18`–`0x1B` |
| EXP 1–2 | `0x36`, `0x37` |
| MIDI (M CFG) | `0x7E` |
| ALL | `0x7F` |

### 1.2 Ale tylko A wolno nadpisać

Fabryczne funkcje A–D (manual Pacera, str. 6–7) i ich realne wykorzystanie w rigu:

| Switch | Fabrycznie | Używane? | Wolno nadpisać? |
|---|---|---|---|
| **A** | Track preset (MCU DAW track select) | ❌ nic tego nie potrzebuje | ✅ **tak** |
| **B** | **Transport preset** → MCU Play/Stop = **nuty 94/93** | ✅ **wyzwala nagrywanie** | ⛔ **nie** |
| **C** | Load previous preset | ✅ nawigacja setlistą (11 utworów) | ⛔ nie |
| **D** | Load next preset | ✅ nawigacja setlistą | ⛔ nie |

`models.py:138–151` pokazuje, dlaczego B jest nietykalne:

```python
record_trigger_channel: int = Field(default=0)   # kanał MIDI 1 (0-indeksowany)
record_start_note:     int = Field(default=94)   # MCU Play  → START
record_stop_note:      int = Field(default=93)   # MCU Stop  → STOP
```

Nadpisanie B zabiera jedyny działający trigger nagrania (PR#30).

### 1.3 Trigger nagrania wymaga trybu modalnego

Dziś: `B` → cały Pacer wchodzi w read-only preset Transport (wszystkie switche
stają się funkcjami MCU) → naciśnięcie Play → nuta 94 → `midi/listener.py` →
`recording/orchestrator.py` → OBS (WebSocket) + forward do Bitwiga.

Dwa naciśnięcia, tryb modalny, i łatwo zostać w złym presecie w środku setu.

Tymczasem listener nasłuchuje **zwykłej nuty** — nie interesuje go, skąd przyszła.
Pacer umie wysłać nutę z dowolnego kroku dowolnego switcha (`MSG_SW_NOTE = 0x43`,
typ `NT`). Czyli trigger może być **jedną z sześciu akcji pierwszego kroku utworu**,
obok memory RC-600, patcha multiefektu i patternu M:S.

Przykład — `data/songs/zen.yaml`, krok 1 ma 4 z 6 akcji zajęte, więc jest miejsce:

```yaml
- device: boss   type: preset   value: 2      # RC-600 memory
- device: freak  type: preset   value: 66     # patch MicroFreaka
- device: ms     type: pattern  value: C01    # pattern perkusji
- device: boss   type: cc       value: 1      # Track 1 Rec/Play
#                                             ← 2 wolne sloty
```

### 1.4 ⛔ Pułapka kanału: nuta z kroku poleci przez DIN

`record_trigger_channel = 0` to **kanał MIDI 1**, a kanał 1 to **MicroFreak**
(`data/devices.yaml`).

Dziś to nie boli: preset Transport nadaje na **PACER MIDI2 (USB)**, czytany
bezpośrednio przez paternologię. Do MicroFreaka to nie dochodzi.

**Ale nuta z normalnego kroku wyjdzie też portem DIN** → RC-600 (MIDI Thru: ON)
→ Doremidi Split/Merge → MicroFreak, który **zagra nutę 94**. Nowy trigger musi
więc siedzieć na **innym kanale** niż jakiekolwiek urządzenie w łańcuchu.

Zajęte kanały (`data/devices.yaml` + faktyczne użycie w 11 piosenkach):
**1** MicroFreak (21×), **5** martwy wpis `ampero` (0×), **13** RC-600 (58×),
**14** Model:Samples (34×), **15** `start_stop` = sceny Bitwiga + trigger OBS (12×).
Wolne: **2, 3, 4, 6–12, 16**.

## Requirements Trace

- **R1.** Eksport SysEx konfiguruje **switch A** (`0x14`) na równi z SW 1–6:
  control mode + 6 kroków, z czyszczeniem nieużywanych kroków.
- **R2.** Eksport **nie tyka** switchy B, C, D (`0x15`–`0x17`) ani externali
  (`0x18`–`0x1B`). Nadpisanie B zabiera nagrywanie, C/D — nawigację setlistą.
- **R3.** UI utworu pozwala edytować akcje switcha A tak samo jak SW 1–6.
- **R4.** Nagrywanie (OBS + Bitwig) da się **przełączyć jedną nutą** wysłaną
  z dowolnego kroku dowolnego switcha.
- **R5.** Nuta toggle jedzie na **konfigurowalnym kanale, domyślnie innym niż
  kanał 1** — inaczej MicroFreak ją zagra.
- **R6.** Istniejąca ścieżka 94/93 z presetu Transport działa **bez zmian**
  (kompatybilność wstecz, zero ryzyka regresji na scenie).
- **R7.** Stan nagrywania jest widoczny w live view paternologii — przy toggle
  operator musi wiedzieć, w którą stronę przełączy.

## Scope Boundaries

**W zakresie:**
- switch A w eksporcie i UI
- jednonutowy toggle nagrywania
- wpis `rec` w `data/devices.yaml`
- odczyt stanu nagrywania z OBS do live view

**Poza zakresem (świadomie odłożone):**
- **Switche B, C, D w eksporcie** — B jest nietykalne (R2), C/D niosą nawigację.
  Gdyby kiedyś zmienić sposób chodzenia po setliście, wracamy do tematu.
- **Externale FS 1–4** (`0x18`–`0x1B`) — Wojtas rozważa Hotone FS-1, ale sprzęt
  nie jest kupiony. Struktura ma być na to gotowa (mapa control ID, nie `range(N)`),
  ale kodu pod nie nie piszemy.
- **Tryb `SEq` per kontroler.** To alternatywna droga do start/stop (krok 1 = nuta
  94, krok 2 = 93) i wymagałaby pola `mode` per switch w modelu. **Odrzucona** —
  patrz Decisions D2.
- **Expression pedals** (`0x36`, `0x37`) — niepodłączone
  (potwierdzone 2026-05-05).
- **Podmiana martwego wpisu `ampero` na `valeton_gp50`** — osobna, niezależna
  zmiana danych, nie kodu.
- **Zmiana `record_trigger_channel`** — nie ruszamy, bo to zerwałoby ścieżkę B (R6).

## Decisions

### D1. Toggle przez `ToggleRecord` w obs-websocket, nie przez własny stan

**Decyzja:** nowa nuta wywołuje **`ToggleRecord`** (request obs-websocket v5),
a nie „zapytaj o stan, potem zrób odwrotność" ani lokalny licznik w paternologii.

**Dlaczego:** stan nagrywania trzyma OBS. Każda lokalna kopia rozjedzie się, gdy
ktoś zatrzyma nagranie z UI OBS-a albo gdy OBS wystartuje ponownie.
`ToggleRecord` jest bezstanowy z punktu widzenia paternologii i **nie da się
zdesynchronizować**.

Strona Bitwiga: ta sama nuta jest forwardowana, a Bitwig ma Transport Record
**MIDI-learned jako toggle**, więc zachowa się spójnie bez dodatkowej logiki.

### D2. Odrzucone: tryb `SEq` na jednym switchu Pacera

Wariant rozważany: jeden switch w trybie `SEq` (`CONTROL_MODE_SEQUENCE = 0x01`),
krok 1 = nuta 94, krok 2 = nuta 93. Zero zmian w logice nagrywania.

**Odrzucone z trzech powodów:**

1. **Desynchronizacja.** Stan trzyma wskaźnik kroku w Pacerze. Zatrzymanie
   nagrania z dowolnego innego miejsca (UI OBS-a, drugi trigger, restart) zostawia
   wskaźnik przekonanym, że „następne naciśnięcie = stop", gdy nic nie nagrywa.
2. **Brak sprzężenia zwrotnego.** LED w Pacerze jest per kontroler, nie per krok —
   nie widać, na którym kroku sekwencji stoisz.
3. **Dwa slots zamiast jednego** i wymóg pola `mode` per switch w modelu, którego
   dziś nie ma (`export.py` twardo `mode=0`).

Uwaga uboczna: `SEq` na **externalach** jest dodatkowo wątpliwy — pacer-editor
wyklucza `0x18`–`0x1B` z `CONTROLS_WITH_SEQUENCE` (zakomentowane), wbrew manualowi.
Dla SW 1–6 i A–D `SEq` jest potwierdzony, ale to nie zmienia powyższych trzech
argumentów.

### D3. Nowa nuta i kanał osobno od 94/93, nie zamiast

Dodajemy **`record_toggle_note`** i **`record_toggle_channel`** jako nowe pola
konfiguracji, obok istniejących `record_start_note` / `record_stop_note` /
`record_trigger_channel`.

**Dlaczego nie przenieść starych:** `record_trigger_channel` musi zostać na 0
(kanał 1), bo taki jest MCU i tak nadaje preset Transport. Zmiana zerwałaby
ścieżkę B (R6) — jedyną dziś sprawdzoną na scenie.

Domyślny kanał toggle: **4** (0-indeksowany `3`) — wolny, z zapasem od zajętych.

### D4. `CONTROLS` jako mapa, nie `range(N)`

`STOMPSWITCHES = {i: 0x0D + i for i in range(6)}` opiera się na tym, że control ID
są ciągłe. **Nie są** — `0x13` to RESERVED, a externale zaczynają się od `0x18`.
Zamiana na jawną mapę indeks→control ID usuwa pułapkę przy przyszłym dodaniu
externali.

## Implementation Units

### U1. Mapa kontrolerów w `constants.py`

**Pliki:**
- `packages/paternologia/src/paternologia/pacer/constants.py`
- test: `packages/paternologia/tests/test_pacer_sysex.py`

**Zmiana:** zamiast `STOMPSWITCHES = {i: 0x0D + i for i in range(6)}` — jawna mapa
z komentarzem, które ID są celowo pominięte:

```python
# Control IDs (Object byte dla control steps/mode/LED).
# Pełna tabela: pacer-editor/src/pacer/constants.js
# NIE dopisywać B/C/D (0x15-0x17) — B wyzwala nagrywanie (preset Transport),
# C/D niosą nawigację po setliście. Patrz docs/plans/2026-09-10-001.
EXPORTED_CONTROLS = {
    0: 0x0D,  1: 0x0E,  2: 0x0F,  3: 0x10,  4: 0x11,  5: 0x12,   # SW 1-6
    6: 0x14,                                                      # SW A
}
CONTROL_FOOTSWITCH_1 = 0x18  # externale — nieeksportowane, na przyszłość
CONTROL_FOOTSWITCH_2 = 0x19
CONTROL_FOOTSWITCH_3 = 0x1A
CONTROL_FOOTSWITCH_4 = 0x1B
```

`STOMPSWITCHES` zostaje jako alias na pierwsze sześć, żeby nie łamać importów
(albo usunięty, jeśli grep pokaże brak innych użyć — sprawdzić w wykonaniu).

**Scenariusze testowe:**
- `EXPORTED_CONTROLS` ma dokładnie 7 wpisów
- indeksy 0–5 mapują na `0x0D`–`0x12` (regresja: dotychczasowe zachowanie)
- indeks 6 mapuje na `0x14`
- `0x13`, `0x15`, `0x16`, `0x17` **nie występują** w wartościach mapy
  (test negatywny — chroni R2)

### U2. Eksport siódmego kontrolera

**Pliki:**
- `packages/paternologia/src/paternologia/pacer/export.py`
- test: `packages/paternologia/tests/test_pacer_export.py`

**Zmiana:** `for btn_idx in range(6)` → iteracja po `EXPORTED_CONTROLS`.
Reszta pętli bez zmian — `build_control_mode(control_id, mode=0)` plus 6 kroków
z czyszczeniem nieużywanych.

**Scenariusze testowe:**
- utwór z 7 przyciskami → SysEx zawiera komunikaty dla `0x0D`–`0x12` **oraz `0x14`**
- utwór z 6 przyciskami → siódmy kontroler dostaje `mode` + 6 kroków `MSG_CTRL_OFF`
  (czyszczenie), tak jak dziś nieużywane SW
- utwór z 3 przyciskami → regresja: kroki 4–6 wszystkich kontrolerów wyczyszczone
- **żaden wygenerowany komunikat nie adresuje `0x15`, `0x16`, `0x17`, `0x18`–`0x1B`**
  (test negatywny, R2 — to najważniejszy test w tej jednostce)
- liczba komunikatów = 1 (nazwa) + 7 × (1 mode + 6 kroków) = 50
- bajt po bajcie względem fixture'a `.syx` (patrz U6)

### U3. Model utworu na 7 przycisków

**Pliki:**
- `packages/paternologia/src/paternologia/models.py`
- test: `packages/paternologia/tests/test_models.py`

**Zmiana:** walidacja długości `pacer` z 6 na `len(EXPORTED_CONTROLS)`, plus
opisowa nazwa kontrolera w modelu (żeby UI mogło wypisać „A" zamiast „7").

**Scenariusze testowe:**
- utwór z 7 przyciskami waliduje się
- utwór z 8 przyciskami → `ValidationError`
- utwór z 0–6 przyciskami waliduje się (regresja — istniejące pliki
  `data/songs/*.yaml` mają 0–6 kroków i **muszą** się ładować bez migracji)
- każdy przycisk nadal max 6 akcji

### U4. UI: siódmy wiersz

**Pliki:**
- `packages/paternologia/src/paternologia/routers/songs.py`
- szablon formularza utworu (ścieżka do ustalenia w wykonaniu — `grep` po
  `pacer_export_target_preset`)
- test: `packages/paternologia/tests/test_api.py`

**Zmiana:** liczba wierszy z `6` na `len(EXPORTED_CONTROLS)`, etykieta „A" dla
siódmego. **`for action_idx in range(6)` w `songs.py:236` zostaje 6** — to pętla
po **krokach**, nie po switchach.

**Scenariusze testowe:**
- POST formularza z 7 przyciskami zapisuje wszystkie 7
- POST z 6 → siódmy zapisany jako pusty, nie gubiony
- GET utworu renderuje 7 wierszy z etykietami `1–6, A`

### U5. Jednonutowy toggle nagrywania

**Pliki:**
- `packages/paternologia/src/paternologia/models.py` (nowe pola konfiguracji)
- `packages/paternologia/src/paternologia/midi/listener.py` (rozpoznanie nuty)
- `packages/paternologia/src/paternologia/recording/orchestrator.py` (akcja toggle)
- `packages/paternologia/src/paternologia/recording/obs_client.py` (`ToggleRecord`)
- `packages/paternologia/data/devices.yaml` (wpis `rec`)
- testy: `tests/test_models.py`, `tests/test_midi_listener.py`,
  `tests/test_orchestrator.py`, `tests/test_obs_client.py`

**Nowe pola konfiguracji:**

```python
record_toggle_channel: int = Field(default=3, ge=0, le=15,
    description="Kanał MIDI (0-15) nuty toggle. Domyślnie 3 = kanał 4. "
                "NIE 0 — kanał 1 to MicroFreak, zagrałby nutę.")
record_toggle_note: int = Field(default=94, ge=0, le=127,
    description="Nuta przełączająca nagrywanie OBS + Bitwig.")
```

Nuta może być ta sama co `record_start_note` (94), bo **rozróżnia je kanał**.

**Wpis w `data/devices.yaml`:**

```yaml
- id: rec
  name: Recording toggle
  description: Paternologia → OBS ToggleRecord + Bitwig Transport Record
  midi_channel: 4
  action_types:
    - note
```

**Scenariusze testowe:**
- Note On `record_toggle_note` na `record_toggle_channel`, velocity > 0 →
  `orchestrator.toggle()` wywołany raz
- ta sama nuta na **innym** kanale → toggle **nie** wywołany
- Note Off / velocity 0 → toggle **nie** wywołany
- nuta 94 na kanale 0 → dalej idzie starą ścieżką `start()`, **nie** `toggle()`
  (regresja, R6)
- nuta 93 na kanale 0 → `stop()` (regresja, R6)
- `obs_client.toggle_record()` wysyła request `ToggleRecord` przez WebSocket
- `ToggleRecord` gdy OBS nieosiągalny → log błędu, brak wyjątku w górę
  (nie wolno wywalić mostu MIDI w środku setu)
- dwa Note On w odstępie < progu dispatchera → **jedno** wywołanie toggle
  (odbicie footswitcha — ten sam mechanizm co `recording/dispatcher.py`)

### U6. Fixture SysEx jako kontrakt

**Pliki:**
- `packages/paternologia/tests/fixtures/` (ścieżka do potwierdzenia — `conftest.py`
  pokaże istniejącą konwencję)
- test: `packages/paternologia/tests/test_pacer_export.py`

**Zmiana:** commitowany plik `.syx` wygenerowany dla znanego utworu z 7 przyciskami,
zweryfikowany w [pacer-editor](https://studiocode.dev/pacer-editor/) (import →
sprawdzenie, że switch A ma oczekiwane kroki, a B/C/D są nietknięte).

Zgodnie z zasadą projektu: **fixture'y są kontraktem parsera i są commitowane**,
karmione realnymi bajtami, nigdy wymyślonymi.

**Scenariusze testowe:**
- eksport utworu referencyjnego == fixture, bajt w bajt
- fixture **nie zawiera** bajtów `0x15`–`0x17` w pozycji control ID

### U7. Stan nagrywania w live view

**Pliki:**
- `packages/paternologia/src/paternologia/recording/obs_client.py`
  (`GetRecordStatus`)
- `packages/paternologia/src/paternologia/routers/live_api.py` (lub `songs.py` —
  do ustalenia)
- test: `tests/test_obs_client.py`, `tests/test_live_api.py`

**Uzasadnienie (R7):** przy toggle operator musi wiedzieć, w którą stronę
przełączy. Bez tego jedno naciśnięcie w niepewności zatrzymuje nagranie utworu.

**Scenariusze testowe:**
- `get_record_status()` mapuje odpowiedź obs-websocket na `bool` + czas trwania
- OBS nieosiągalny → status `None`, endpoint nie rzuca 500
- endpoint live zwraca stan nagrywania w payloadzie

## Dependencies & Sequencing

```
U1 (mapa control ID)
 ├─► U2 (eksport)  ──► U6 (fixture — weryfikuje U1+U2 na realnych bajtach)
 └─► U3 (model)    ──► U4 (UI)

U5 (toggle)  ─── niezależne od U1-U4, można równolegle
 └─► U7 (stan w live view)
```

**Dwie niezależne gałęzie.** U1–U4+U6 to „switch A", U5+U7 to „toggle nagrywania".
Można wydać osobno; nic ich nie łączy poza tym, że nowa nuta toggle najprawdopodobniej
zamieszka w kroku któregoś switcha (być może właśnie A).

Kolejność w praktyce: **U5+U7 najpierw** — rozwiązuje realną niedogodność scenicznej
obsługi, a U1–U4 tylko zwiększa pojemność, której dziś nie brakuje (utwory używają
1–6 kroków z 36 dostępnych slotów).

## Risks

| Ryzyko | Skala | Mitygacja |
|---|---|---|
| **Eksport nadpisuje B i zabiera nagrywanie** | ⛔ **krytyczna** — traci się nagrywanie na scenie | Test negatywny w U2 i U6 sprawdzający, że `0x15`–`0x17` nie występują jako control ID. To najważniejszy test w całym planie |
| Eksport nadpisuje C/D i zabiera nawigację setlistą | wysoka | ten sam test |
| Nuta toggle zagrana przez MicroFreaka | średnia | domyślny kanał 4, walidacja `ge=0`, opis pola ostrzegający przed 0. Test: nuta na innym kanale nie wywołuje toggle |
| Toggle rozjeżdża się ze stanem OBS | niska | `ToggleRecord` jest bezstanowy po stronie paternologii (D1); U7 pokazuje realny stan |
| Odbicie footswitcha podwaja toggle | średnia | istniejący `recording/dispatcher.py` — test w U5 |
| Regresja na istniejących `data/songs/*.yaml` | średnia | testy regresji w U3 na utworach z 0–6 przyciskami; **żadnej migracji danych** |
| `WebSocket ToggleRecord` niedostępny w wersji obs-websocket Wojtasa | niska | `ToggleRecord` jest w obs-websocket v5, a `obs.yaml` już deklaruje v5. Do potwierdzenia w wykonaniu — fallback: `GetRecordStatus` + `StartRecord`/`StopRecord` |

## Execution Posture

**Test-first.** Reguła projektu i osobista Wojtasa: testy przed implementacją,
tylko tyle kodu, żeby przechodziły, refactor przy zielonych.

Kolejność w każdej jednostce: **najpierw test negatywny** (co nie może się stać),
potem pozytywny. W U2 to nie kosmetyka — test „nie adresujemy `0x15`–`0x17`"
chroni funkcję, której utrata jest odkrywana dopiero na scenie.

Fixture SysEx (U6) karmiony **realnymi bajtami** zweryfikowanymi w pacer-editorze,
nigdy wymyślonymi.

## Deferred to Execution

- Dokładna ścieżka szablonu formularza utworu (U4) — `grep` po
  `pacer_export_target_preset`
- Konwencja katalogu fixture'ów (U6) — `conftest.py`
- Czy `STOMPSWITCHES` ma zostać jako alias, czy da się usunąć (U1) — `grep` po
  użyciach
- Czy wersja obs-websocket u Wojtasa wspiera `ToggleRecord` (U5)
- Czy Bitwig faktycznie zachowa się jak toggle na powtórzonej nucie, czy trzeba
  osobnego mapowania (U5) — weryfikacja na sprzęcie

## Open Questions

- ~~**Co wsadzić na switch A?**~~ **Rozstrzygnięte 2026-09-10: nuta toggle
  nagrywania.** Jedno pewne miejsce, niezależne od tego, który preset jest
  załadowany. Wiąże U1–U4 z U5+U7 — obie gałęzie planu spotykają się na tym
  jednym switchu, ale nadal można je wydać osobno (toggle działa z dowolnego
  kroku dowolnego switcha; `A` to tylko docelowe miejsce).
  Odrzucony kandydat `ALL ST/STP` — patrz niżej.
- **Czym są CC 10 i CC 13** wysyłane do RC-600 na kanale 13? Bez labelek
  w `data/songs/*.yaml`. Operator (2026-09-10): *„najczęściej to mapowanie
  włączania nagrywania lub efektów w RC-600"* — czyli **track rec albo FX on/off**,
  w każdym razie **nie `ALL ST/STP`**. To domyka wątpliwość, czy `A` jest wolne:
  jest. Sam test schodzi do higieny danych (dopisanie labelek), nie blokuje planu.
- **Higiena labelek** w konfigach utworów: 8 wystąpień CC 1 ma `label: None`,
  CC 2 ma `label: null` w dwóch, a CC 1 raz nosi „Track 1 Rec/Play", raz
  „nagraj gitarę (track2)". Nie zmienia zachowania, ale utrudnia czytanie mapy CC.
  Osobne zadanie porządkowe.
