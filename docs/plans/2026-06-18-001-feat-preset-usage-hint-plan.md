---
title: "feat: Podpowiedź zajętości presetu/patternu + zgodne numery presetów w UI"
type: feat
status: completed
date: 2026-06-18
---

# feat: Podpowiedź zajętości presetu/patternu + zgodne numery presetów w UI

## Overview

Dwie powiązane zmiany w edytorze utworów paternologii:

1. **Podpowiedź zajętości** — gdy użytkownik wybiera preset (Boss, Freak, Ampero) lub pattern
   (M:S) dla urządzenia, pod polem wartości pojawia się podpowiedź (kaskada HTMX): czy ten slot
   jest już użyty w innych utworach (z listą ich nazw), czy jest wolny. Cel: nie nadpisać /
   nie naruszyć presetu lub patternu, który jest fizycznym, współdzielonym slotem na sprzęcie.
2. **Zgodne numery presetów w UI** — numer presetu pokazywany i wpisywany w interfejsie jest
   zgodny z numerem widocznym na ekranie urządzenia. Dziś dla Boss i Freak występuje przesunięcie
   o jeden. Korekta dzieje się **transparentnie** przez **ukryty offset konfiguracyjny** w
   `devices.yaml` — użytkownik nigdy nie widzi „przesunięcia" ani samego pola offsetu, tylko
   spójny numer. Przechowywany `value` pozostaje surowym numerem MIDI.

## Problem Frame

Presety i paterny w utworach to **referencje do fizycznych slotów na sprzęcie** (numer programu
na Boss/Freak/Ampero, slot patternu A0–F06 na Model:Samples). Aplikacja przechowuje tylko
odwołania, nie samą zawartość. Dwa problemy autora:

- **Współdzielenie slotów (problem 1):** ten sam slot referowany przez kilka utworów to ten sam
  fizyczny zasób — przeprogramowanie go pod jeden utwór zmienia inny. Dziś, edytując, autor nie
  widzi, czy numer jest już „zajęty" przez inny utwór.
- **Off-by-one w numeracji (problem 2):** przechowywany `value` to surowy numer MIDI Program
  Change (0-based; `pacer/mappings.py:action_to_midi` robi `prog = value % 128`). Boss i Freak
  wyświetlają presety 1-based, więc numer w UI rozjeżdża się z ekranem urządzenia o jeden, co
  prowadzi do konfuzji. Pattern M:S jest zgodny (osobna konwencja, autor potwierdza brak rozjazdu).

## Requirements Trace

- R1. Po wybraniu urządzenia + typu (`preset`/`pattern`) i wpisaniu wartości, pod polem pojawia
  się informacja o zajętości tego slotu w **innych** utworach.
- R2. Gdy slot nie jest użyty w żadnym innym utworze — podpowiedź jasno komunikuje „wolny".
- R3. Gdy slot jest użyty — podpowiedź wymienia nazwy utworów, które go używają.
- R4. Bieżąco edytowany utwór jest wykluczany z listy.
- R5. Mechanizm działa tak samo dla nowego utworu (`/songs/new`) jak i edycji istniejącego.
- R6. Numer presetu pokazywany w UI i wpisywany przez użytkownika jest zgodny z numerem na
  ekranie urządzenia (Boss, Freak; Ampero konfigurowalny na przyszłość).
- R7. Offset jest **ukrytą konfiguracją** w `devices.yaml`, niewidoczną i nieedytowalną z poziomu
  UI; użytkownik nie widzi „przesunięcia" ani wartości offsetu. Pattern M:S bez zmian (offset 0).

## Scope Boundaries

- **Tylko typy `preset` i `pattern`** dla podpowiedzi zajętości. Akcje `cc`/`note` to chwilowe
  komunikaty, nie sloty — nie są śledzone.
- **Tylko lista utworów, bez analizy konfliktu etykiet** (decyzja użytkownika).
- **„Wolny" = nieużywany w innych utworach**, nie „wolny w przestrzeni slotów urządzenia".
- **Offset numeracji jest WYŁĄCZNIE wyświetlaniem i jest ukryty.** Przechowywany `value` w YAML
  pozostaje surowym numerem MIDI. **Bez zmian w eksporcie** (`pacer/`), **bez zmian w detekcji
  live** (`midi/index.py`), **bez migracji istniejących plików utworów**. To celowe: eksport do
  Pacera działa i jest wrażliwy (ryzyko zbrickowania), więc go nie ruszamy.
- **Offset NIE jest wystawiany w żadnym UI.** Widok `/devices` jest tylko do odczytu (brak
  formularzy edycji), a edytor utworu nie pokazuje pola offsetu — wartość żyje wyłącznie w
  `devices.yaml` (edycja ręczna / konfiguracyjna).
- Offset dotyczy tylko typu `preset` (numeryczny). Pattern (string) bez offsetu.
- Spójne wyświetlanie numeru presetu poza edytorem (widok `song.html`, lista) — patrz Deferred.

## Context & Research

### Relevant Code and Patterns

- **`packages/paternologia/src/paternologia/midi/index.py` (`SongMidiIndex`)** — wzorzec klasy
  z `build(songs, devices)` skanującej wszystkie utwory i `lookup(...)`. Nowy indeks zajętości
  ma identyczny kształt. **Pozostaje bez zmian** (operuje na surowym `value`).
- **`packages/paternologia/src/paternologia/pacer/mappings.py` (`action_to_midi`)** — tu żyje
  konwersja `value` → MIDI (`prog = value % 128`, `bank_msb = value // 128`). **Bez zmian** —
  potwierdza, że przechowywany `value` to surowy numer MIDI, więc offset musi być tylko nakładką
  wyświetlania.
- **`packages/paternologia/src/paternologia/models.py`** — `Device` (dodamy ukryte pole offsetu),
  `Action(device, type, value, label, …)`, `ActionType`. Preset `value: int`, pattern `value: str`.
- **`packages/paternologia/src/paternologia/storage.py` (`Storage`)** — `get_songs()`,
  `get_devices()`. Źródło danych.
- **`packages/paternologia/src/paternologia/routers/{songs,devices}.py`** — `devices.py` ma tylko
  listę/JSON urządzeń (read-only, brak edycji). `songs.py` ma partiale HTMX
  (`/partials/action-types`, `/partials/action-fields`) i `_build_song_from_form` (tu konwersja
  numer-urządzenia → surowy `value`). Nowy endpoint `/partials/preset-usage`.
- **`packages/paternologia/templates/partials/{action_fields,action_row}.html`** — render pól i
  wzorzec kaskady HTMX (`hx-get`, `hx-target="next ..."`, `hx-vals="js:{...}"`).
- **`packages/paternologia/templates/song_edit.html`** — formularz edycji; udostępnimy ID
  bieżącego utworu (`data-song-id`).

### Institutional Learnings

- Brak wpisu w `docs/solutions/` o paternologii. Najbliższy wzorzec to `SongMidiIndex` w repo.
- Z pamięci agenta: pełne `uv run pytest` bywa zepsute — testować po ścieżce pakietu
  (`uv run --package paternologia pytest packages/paternologia/tests/...`).
- Z pamięci agenta: eksport do Pacera jest krytyczny (ostrzeżenia o brickowaniu) — stąd decyzja,
  by offset był display-only i nie dotykał ścieżki SysEx.

### External References

- Pominięto research zewnętrzny: funkcja jest mała, w pełni wewnętrzna (FastAPI + HTMX + Jinja2),
  z silnym lokalnym wzorcem (`SongMidiIndex`) i kompletem konwencji partiali HTMX.

## Key Technical Decisions

- **Offset jako ukryte pole konfiguracyjne `Device.preset_display_offset`** (int, default 0) w
  `devices.yaml`. Konwencja: `offset = (numer na ekranie urządzenia) − (surowy value MIDI)`;
  `displayed = stored + offset`, `stored = entered − offset`. Boss/Freak → `1`; M:S → `0`.
  Rationale: spełnia R6/R7 bez dotykania działającego eksportu i bez migracji plików; pole nie
  jest wystawiane w UI (widok urządzeń jest read-only). Offset signed → odporny, gdyby któreś
  urządzenie miało inny kierunek/wielkość.
- **Korekta jest transparentna dla użytkownika.** W edytorze widzi i wpisuje numer urządzenia;
  offset nakładany/zdejmowany pod spodem. Użytkownik nigdy nie widzi „przesunięcia" ani offsetu.
- **Centralne helpery konwersji** `to_display(value, device)` / `to_stored(value, device)` dla
  typu `preset` (DRY — render edytora, parsowanie formularza, endpoint podpowiedzi). Pattern i
  inne typy: tożsamość.
- **Osobny indeks zajętości `PresetUsageIndex`, kluczowany na SUROWYM `value`.** Nie rozszerzamy
  `SongMidiIndex` (inny cel: pełna lista per slot, nie first-match dla live). Dopasowanie na
  surowych wartościach (spójnych z plikami); offset to tylko warstwa prezentacji.
- **Indeks budowany na żądanie z `storage.get_songs()` w endpoincie, bez cache w `app.state`.**
  Rationale: dziesiątki utworów, tani skan, krytyczna świeżość po zapisie; cache ryzykowałby
  nieaktualne podpowiedzi.
- **Typ akcji stały w gałęzi szablonu** → `action_type` jako literał w `hx-vals`; `device_id` i
  `value` czytane na żywo z DOM. Spójne z istniejącym wzorcem kaskady.

## Open Questions

### Resolved During Planning

- *Gdzie żyją presety/paterny?* — Wyłącznie w `pacer[].actions[]` (model `Song` nie ma już bloku
  `devices:` z SPEC-a; potwierdzone na `swit.yaml`, `a1-w-ciszy-learn.yaml`).
- *„Wolny" = wolny na sprzęcie?* — Nie; „nieużywany w innych utworach".
- *Prezentacja podpowiedzi?* — Inline przy polu (kaskada HTMX), nie osobna mapa.
- *Konflikt etykiet?* — Tylko lista utworów, bez analizy `label`.
- *Czy offset ma zmieniać eksport/MIDI?* — Nie. Display-only; przechowywany `value` i ścieżka
  SysEx/live bez zmian.
- *Gdzie żyje offset i czy użytkownik go widzi?* — Ukryte pole w `devices.yaml` (konfiguracja),
  niewidoczne i nieedytowalne w UI; korekta transparentna (użytkownik: „nie muszę widzieć w
  edytorze przesunięcia", „pole offsetu ma być ukryte i być częścią konfiguracji").
- *Których urządzeń dotyczy offset?* — Boss i Freak (off-by-one). M:S zgodny → 0. Ampero brak
  sprzętu → pole domyślnie 0, do uzupełnienia później.

### Deferred to Implementation

- **Dokładny offset dla Ampero** — gdy sprzęt się pojawi; pole już będzie gotowe.
- **Spójny numer presetu poza edytorem** (widok `song.html`, lista) — ten sam helper `to_display`
  można tam podpiąć; rozważyć po wdrożeniu edytora.
- **Czy pokazywać podpowiedź od razu przy otwarciu edycji** (trigger `load`) czy dopiero przy
  zmianie wartości — rozstrzygnąć przy implementacji szablonu.
- Dokładny debounce triggera `keyup` (~300–500 ms).

## Implementation Units

- [x] **Unit 1: Ukryty offset numeru presetu (model + helpery konwersji)**

**Goal:** Numer presetu w UI zgodny z ekranem urządzenia, korygowany transparentnie przez ukryte
pole konfiguracyjne; bez zmian w przechowywanym `value` ani w eksporcie.

**Requirements:** R6, R7

**Dependencies:** Brak.

**Files:**
- Modify: `packages/paternologia/src/paternologia/models.py` (pole `Device.preset_display_offset`)
- Create: `packages/paternologia/src/paternologia/display.py` (helpery `to_display`/`to_stored`)
- Modify: `packages/paternologia/data/devices.yaml` (offset 1 dla boss/freak; 0/brak dla ms)
- Test: `packages/paternologia/tests/test_display.py`
- Test: `packages/paternologia/tests/test_models.py` (default offsetu)

**Approach:**
- `Device.preset_display_offset: int = Field(default=0, description="Ukryty offset wyświetlania
  numeru presetu (ekran urządzenia − surowy MIDI); konfiguracja, nie wystawiana w UI")`. Domyślnie
  0 → urządzenia bez pola działają jak dziś (M:S, nieskonfigurowane).
- `display.py`: `to_display(value, device)` — dla `preset`-owej wartości numerycznej zwraca
  `value + device.preset_display_offset`; `to_stored(value, device)` — `value − offset`. Pattern/
  inne: zwraca wejście bez zmian. Jedna reguła, dwie strony (DRY); round-trip
  `to_stored(to_display(v)) == v`.
- `devices.yaml`: dodać `preset_display_offset: 1` do `boss` i `freak`. (Nie pokazywane w UI —
  widok `/devices` jest read-only.)

**Patterns to follow:**
- Pola `Device` w `models.py` (np. `midi_channel` z `Field(..., ge=, le=)`).

**Test scenarios:**
- Happy path: `to_display(100, boss)` → `101`; `to_stored(101, boss)` → `100`.
- Round-trip: dla zakresu wartości `to_stored(to_display(v)) == v`.
- Edge: urządzenie bez offsetu (M:S, default 0) → `to_display`/`to_stored` to tożsamość.
- Edge: pattern (string) → offset nie stosowany.
- Edge: `value` None/pusty → bez wyjątku, zwraca wejście.
- Model: `Device` bez pola w YAML → `preset_display_offset == 0`.

**Verification:**
- `test_display.py` i `test_models.py` zielone; konwersja per urządzenie działa, pattern nietknięty.

---

- [x] **Unit 2: Indeks zajętości `PresetUsageIndex`**

**Goal:** Czysta (bez web) struktura mapująca slot `(device, type, surowy value)` na listę
utworów, z wykluczaniem wskazanego utworu w odpytaniu.

**Requirements:** R1, R3, R4

**Dependencies:** Brak (operuje na surowym `value`, niezależnie od Unit 1).

**Files:**
- Create: `packages/paternologia/src/paternologia/usage.py`
- Test: `packages/paternologia/tests/test_usage.py`

**Approach:**
- `PresetUsageIndex` wzorowany na `SongMidiIndex`: `@classmethod build(songs)` skanuje
  `song.pacer[].actions[]`, bierze tylko `PRESET`/`PATTERN` z niepustą `value`, normalizuje
  (preset → `int`, pattern → `str.strip().upper()`), akumuluje `klucz → list[wpis(song_id, song_name)]`.
- `lookup(device_id, action_type, value, exclude_song_id=None)` normalizuje wartość tak samo,
  zwraca utwory używające slotu z pominięciem `exclude_song_id`, deduplikuje powtórne użycie w
  obrębie jednego utworu, zachowuje kolejność z `get_songs()`.
- Normalizacja wydzielona do jednej funkcji (DRY — klucz identyczny w `build` i `lookup`).

**Patterns to follow:**
- `midi/index.py` — kształt `build`/`lookup`, logowanie pomijanych akcji, iteracja po przyciskach.

**Test scenarios:**
- Happy path: dwa utwory używają `boss/preset/4` → lookup zwraca oba (z nazwami).
- Happy path (pattern): `ms/pattern/F03` w dwóch utworach; klucz odporny na wielkość liter/spacje.
- Edge: slot tylko w jednym utworze + `exclude_song_id` ten utwór → pusta lista.
- Edge: ten sam slot w dwóch przyciskach jednego utworu → utwór raz (dedup).
- Edge: `value` None/pusty → akcja pomijana.
- Edge: `cc`/`note` → ignorowane.
- Edge: preset `int` vs pattern `str` nie kolidują (różny `action_type` w kluczu).

**Verification:**
- `test_usage.py` zielone; grupowanie, wykluczanie i normalizacja patternu działają.

---

- [x] **Unit 3: Endpoint i partial podpowiedzi `/partials/preset-usage`**

**Goal:** Endpoint HTMX zwracający fragment HTML: „używany też w: …" albo „wolny", dla
`(device_id, action_type, value)` z wykluczeniem bieżącego utworu; wartość z UI (numer
urządzenia) konwertowana na surowy `value` przed dopasowaniem.

**Requirements:** R1, R2, R3, R4, R5

**Dependencies:** Unit 2 (indeks), Unit 1 (helper `to_stored` do konwersji wartości z UI).

**Files:**
- Modify: `packages/paternologia/src/paternologia/routers/songs.py`
- Create: `packages/paternologia/templates/partials/preset_usage.html`
- Test: `packages/paternologia/tests/test_api.py`

**Approach:**
- `GET /partials/preset-usage` z query: `device_id`, `action_type`, `value` (numer z UI, str),
  `song_id` (opcjonalny). Jeśli `action_type` nie jest `preset`/`pattern` albo `value`
  puste/niepełne → pusty fragment. W przeciwnym razie: pobierz device, dla `preset` zamień numer
  z UI na surowy przez `to_stored(value, device)` (pattern bez konwersji), zbuduj
  `PresetUsageIndex` z `storage.get_songs()`, `lookup(..., exclude_song_id=song_id)`, przekaż do
  partiala.
- `preset_usage.html`: lista niepusta → „⚠ używany też w: «Nazwa1», «Nazwa2»"; pusta → „✓ wolny
  (nieużywany w innych utworach)". Styl spójny z `action_fields.html`.

**Patterns to follow:**
- `get_action_fields`/`get_action_types` w `routers/songs.py` — sygnatura handlera, `get_storage`/
  `get_templates`, zwrot `TemplateResponse("partials/...", {...})`.

**Test scenarios:**
- Happy path: dwa utwory współdzielą `boss/preset` (numer UI np. 5 → stored 4); GET z `song_id`
  jednego → odpowiedź zawiera nazwę drugiego, nie bieżącego.
- Happy path (wolny): slot tylko w bieżącym utworze → tekst „wolny".
- Edge: `value` puste → minimalny fragment.
- Edge: `action_type=cc` → pusty fragment.
- Edge: `song_id` pusty (nowy utwór) → nic nie wykluczane.
- Edge (offset): numer UI dla boss (offset 1) poprawnie konwertowany na surowy `value` przed
  lookupem — dopasowuje utwory zapisane surowo.
- Integration: utwór zapisany przez `PUT /songs/{id}`, potem GET `/partials/preset-usage`
  odzwierciedla świeży stan (dowód braku nieaktualnego cache).

**Verification:**
- Nowe testy `test_api.py` zielone; endpoint zwraca poprawny HTML i respektuje `song_id` + offset.

---

- [x] **Unit 4: Wpięcie w formularz edycji (HTMX + transparentny numer)**

**Goal:** Pole wartości presetu/patternu odpytuje `/partials/preset-usage` i pokazuje wynik pod
polem; pole presetu transparentnie pokazuje/przyjmuje numer urządzenia (offset pod spodem), a
zapis konwertuje na surowy `value`. Użytkownik nie widzi offsetu.

**Requirements:** R1, R2, R5, R6

**Dependencies:** Unit 3 (endpoint), Unit 1 (helpery + offset urządzeń w kontekście szablonu).

**Files:**
- Modify: `packages/paternologia/templates/partials/action_fields.html`
- Modify: `packages/paternologia/templates/partials/action_row.html` (przekazanie device do pól)
- Modify: `packages/paternologia/templates/song_edit.html` (`data-song-id` na `<form>`)
- Modify: `packages/paternologia/src/paternologia/routers/songs.py` (`_build_song_from_form`:
  `to_stored` dla presetu; endpointy partiali przekazują device do kontekstu)
- Test: `packages/paternologia/tests/test_api.py`

**Approach:**
- `song_edit.html`: `data-song-id="{{ song.song.id if song else '' }}"` na `<form>`.
- `action_fields.html`, gałęzie `preset`/`pattern`: input `..._value` renderuje **numer
  wyświetlany** (`to_display(action.value, device)` dla presetu; pattern bez zmian) i dostaje
  `hx-get="/partials/preset-usage"`, `hx-target` na sąsiedni `<div class="preset-usage">`,
  `hx-trigger="change, keyup changed delay:400ms"`, `hx-vals="js:{...}"` (device_id z selecta w
  `closest('.action-row')`, `action_type` literałem gałęzi, `value` z `event.target.value`,
  `song_id` z `form[data-song-id]`).
- `_build_song_from_form`: dla `preset` zamień wpisany numer (UI) na surowy przez
  `to_stored(value, device)` zanim zbudujesz `Action`. Pattern/cc/note bez zmian.
- Endpointy renderujące pola (`get_action_fields`, render istniejących akcji) muszą mieć dostęp do
  `device` (dla `to_display`) — przekazać device w kontekście, spójnie z istniejącym `devices`.

**Technical design:** *(directional, nie specyfikacja)*
```
<input ... name="button_{i}_action_{j}_value"
       value="{{ to_display(action.value, device) if action else '' }}"   // preset: stored+offset
       hx-get="/partials/preset-usage"
       hx-target="next .preset-usage"
       hx-trigger="change, keyup changed delay:400ms"
       hx-vals='js:{ device_id: <select _device w closest(.action-row)>,
                     action_type: "preset",
                     value: event.target.value,         // numer urządzenia; endpoint robi to_stored
                     song_id: <form[data-song-id].dataset.songId || ""> }'>
<div class="preset-usage text-xs ..."></div>
// zapis: _build_song_from_form → to_stored(value, device) dla presetu
```

**Patterns to follow:**
- `action_row.html` — `hx-get` + `hx-target="next ..."` + `hx-vals="js:{...}"` + `hx-indicator`.

**Test scenarios:**
- Happy path: GET `/songs/{id}/edit` renderuje pola preset/pattern z `hx-get` na
  `/partials/preset-usage` i kontenerem `.preset-usage`.
- Happy path (offset): utwór z `boss preset` surowym `value=4` renderuje w polu `5` (offset 1);
  offset ani jego pole nie pojawiają się w HTML jako edytowalne.
- Round-trip: render `5` → submit → `_build_song_from_form` zapisuje surowy `4` (plik niezmieniony
  względem konwencji MIDI).
- Edge: `/songs/new` → `<form data-song-id="">`; pole presetu puste.
- Edge: gałąź `cc`/`note` NIE dostaje triggera podpowiedzi ani offsetu.
- Edge: pattern renderowany bez offsetu (M:S zgodny).
- Integration: render edycji + symulowane GET `/partials/preset-usage` z wartością z formularza
  → poprawna podpowiedź (łączy Unit 3 i wpięcie szablonu).

**Verification:**
- Strona edycji i nowego utworu renderują się; pola preset/pattern mają wpięty HTMX + kontener
  podpowiedzi; numer presetu w UI zgodny z urządzeniem, bez widocznego offsetu; zapis odtwarza
  surowy `value`.

## System-Wide Impact

- **Interaction graph:** Nowy endpoint partiala dołącza do rodziny `/partials/*`. Offset zmienia
  render pól i parsowanie formularza, ale **nie** dotyka `export_song_to_syx`/`action_to_midi`
  ani `SongMidiIndex` (te dalej operują na surowym `value`).
- **Error propagation:** Podpowiedź jest best-effort — brak/niepełne parametry → pusty fragment,
  nigdy błąd blokujący edycję. Konwersja offsetu odporna na None/pusty.
- **State lifecycle risks:** Indeks budowany na żądanie → zawsze świeży. Round-trip
  display↔stored musi być tożsamością, inaczej zapis dryfowałby o offset przy każdej edycji —
  pokryte testem round-trip (Unit 1 i Unit 4).
- **API surface parity:** Offset stosowany w edytorze; widok `song.html`/lista mogą wymagać tej
  samej nakładki dla spójności (Deferred). Eksport i widok urządzeń celowo bez zmian.
- **Data integrity:** Brak migracji — przechowywany `value` zachowuje znaczenie (surowy MIDI);
  istniejące pliki działają bez zmian, w UI wyświetlą się z offsetem.
- **Integration coverage:** Testy round-trip (render→submit→stored) i zapis→odczyt świeżego stanu
  dowodzą poprawności tam, gdzie testy jednostkowe nie sięgają.

## Risks & Dependencies

- **Spójność offsetu na obu krańcach (display ↔ stored).** Jeśli render dodaje offset, a zapis go
  nie odejmuje (lub odwrotnie), wartości dryfują przy każdym zapisie. Mitygacja: jedna para
  helperów `to_display`/`to_stored` + test round-trip; offset stosowany TYLKO w warstwie
  edytora/parsowania, nigdy w eksporcie/indeksie.
- **Kierunek/wielkość offsetu zakładane jako +1 dla Boss/Freak.** Mitygacja: pole signed i
  konfigurowalne per urządzenie; weryfikacja empiryczna na sprzęcie po wdrożeniu.
- **Odczyt `device_id` z DOM w `hx-vals`** zależy od struktury `.action-row` i nazwy selecta
  `..._device`. Mitygacja: `closest('.action-row')` + `select[name$=_device]`, spójnie z
  renumeracją w `song_edit.html`.
- **Pattern jako string o niejednolitej wielkości liter** — normalizacja `strip().upper()` (Unit 2).
- Brak zależności zewnętrznych; eksport, format YAML i ścieżka SysEx nietknięte.

## Sources & References

- Konwersja MIDI (dowód, że `value` jest surowy): `packages/paternologia/src/paternologia/pacer/mappings.py`
- Wzorzec indeksu: `packages/paternologia/src/paternologia/midi/index.py` (`SongMidiIndex`)
- Model danych: `packages/paternologia/src/paternologia/models.py`
- Urządzenia read-only w UI: `packages/paternologia/src/paternologia/routers/devices.py`
- Endpointy partiali HTMX i parsowanie formularza: `packages/paternologia/src/paternologia/routers/songs.py`
- Szablony edycji: `packages/paternologia/templates/song_edit.html`,
  `packages/paternologia/templates/partials/{action_fields,action_row}.html`
- Pliki utworów potwierdzające strukturę: `packages/paternologia/data/songs/{swit,a1-w-ciszy-learn}.yaml`
