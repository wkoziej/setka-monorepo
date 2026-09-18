---
title: "feat: Wsparcie Paternologii na macOS"
type: feat
status: active
date: 2026-09-18
deepened: 2026-09-18
---

# feat: Wsparcie Paternologii na macOS

## Overview

`paternologia` (`packages/paternologia`) jest dziś zbudowana z założeniem Linuksa: README
wymienia `amidi` (ALSA CLI) jako zewnętrzną zależność do komunikacji z Pacerem, a
`deploy/paternologia.service` to systemd unit. Cel tego planu: uruchomienie i praca
z aplikacją na macOS do celów **dev/lokalnych** (edycja utworów, live view, MIDI
in/out, bridge do Bitwiga) — bez zmiany zachowania na Linuksie i bez dorabiania
launchd-owego odpowiednika systemd (poza zakresem, patrz Scope Boundaries).

Ręczna weryfikacja w tej samej sesji (macOS, `uv run fastapi run src/paternologia/main.py`,
Pacer podłączony przez USB) potwierdziła, że **`python-rtmidi` (już zależność pakietu)
obsługuje Pacera na macOS przez wbudowany backend CoreMIDI bez żadnej dodatkowej
konfiguracji**:

- `MidiListener` widzi i czyta oba porty (`PACER MIDI1`, `PACER MIDI2`) — dokładnie jak
  na Linuksie (`midi/listener.py`, `midi/ports.py::find_rtmidi_ports`).
- `MidiBridge` (fan-out do Bitwiga) otwiera wirtualny port CoreMIDI `setka-bridge` —
  na macOS to jest *prostsze* niż na Linuksie, bo Bitwig widzi wirtualne porty CoreMIDI
  bezpośrednio (nie ma tam ekwiwalentu problemu "ALSA seq niewidoczne dla Bitwiga",
  patrz `docs/solutions/2026-06-02-bitwig-alsa-seq-invisible-virmidi-bridge.md`).
- `obsws-python` (OBS WebSocket) i FastAPI/HTMX/Jinja2 są czysto sieciowe/Pythonowe —
  bez zależności platformowych.
- `_sd_notify()` (`main.py`) jest już bezpieczny cross-platform: no-op, gdy
  `NOTIFY_SOCKET` nie jest ustawione (czyli zawsze na macOS, poza systemd).

**Jedyna realna dziura:** wysyłka `.syx` do Pacera (`POST /pacer/send/{song_id}`,
`routers/pacer.py`) idzie przez `subprocess.run(["amidi", ...])`, a `amidi` jest
pakietem `alsa-utils` — nie istnieje na macOS. To całkowicie blokuje jedną z dwóch
głównych funkcji Pacer-workflow (eksport `.syx` działa, wysyłka nie).

## Problem Frame

`find_amidi_port()` (`midi/ports.py`) parsuje `amidi -l`, a `send_to_pacer()`
(`routers/pacer.py:50-161`) wywołuje `amidi -p <port> --sysex-interval=<ms> -s <tmpfile>`
na wykrytym porcie. Na macOS `amidi` nie istnieje →
`find_amidi_port()` zawsze zwraca `None` → endpoint zawsze odpowiada 400
"Nie znaleziono urządzenia" (patrz `midi/ports.py:11-37`).

Historyczny kontekst (`SPEC_PACER_BRIDGE.md:465-488`): `amidi` był wybrany świadomie
nad `python-rtmidi` w pierwszej wersji projektu, ale **nie z powodu problemu z
rtmidi** — z powodu szybkości wdrożenia ("działa od razu", "1 tydzień vs 2-3
tygodnie"). `python-rtmidi` był już wtedy oceniony jako technicznie wykonalny
("Spec 1"), tylko droższy w czasie. Dziś `python-rtmidi` jest i tak zależnością
pakietu (`midi/listener.py`, `midi/bridge.py`), więc koszt tej samej decyzji jest
dziś dużo niższy.

Zewnętrzne badanie (RtMidi.cpp, `thestk/rtmidi#214`, python-rtmidi API docs)
ujawniło ważny niuans: `MidiOut.send_message()` **nie blokuje do faktycznego
wysłania** na żadnym z dwóch celowych backendów (ALSA sequencer, CoreMIDI) — w
obu przypadkach zwraca się po "zakolejkowaniu", nie po dostarczeniu. `amidi`
używał innej ścieżki ALSA (`rawmidi`, blokujący `write()`), więc `--sysex-interval=20`
było paced na tym samym poziomie abstrakcji co dziś proponowana zamiana. Backend
ALSA-sequencer, który `python-rtmidi` faktycznie używa na Linuksie, ma
udokumentowany (upstream, `rtmidi` issue #214) **silent-drop** dla SysEx, gdy
nadawca wyprzedza tempo odbioru — bez wyjątku, po prostu ubytek bajtów. To
oznacza, że natywna wysyłka może na Linuksie być *inaczej* zawodna niż `amidi`,
nie tylko "tak samo dobra" — stąd wymóg realnej weryfikacji sprzętowej w U1/U2
(patrz Risks).

## Requirements Trace

- R1. Wysyłka `.syx` do Pacera (`POST /pacer/send/{song_id}`) działa identycznie
  na Linuksie i macOS, bez zewnętrznego binarki `amidi` — **warunkowo na
  przejściu bramki weryfikacyjnej (Unit 2 Verification, STATUS: PASS)**. Jeśli
  bramka nie przejdzie na Linuksie, R1 dla tej platformy nie jest spełniony w
  wersji "jeden sender" — patrz rollback w Risks & Dependencies i Key
  Technical Decisions.
- R2. Pacing między wiadomościami SysEx (dziś `--sysex-interval=20`) jest
  zachowany na obu platformach — to jest CRITICAL wymaganie sprzętowe Pacera
  (`data/pacer.yaml:12-14`), nie kosmetyka.
- R3. Istniejący kontrakt HTTP endpointu (kody błędów 400/404/500, treść
  komunikatów gdzie to możliwe) nie regresuje na Linuksie.
- R4. Dokumentacja (README, UI usage instructions, `pacer.yaml`) nie wprowadza
  w błąd — nie każe użytkownikowi macOS uruchamiać `amidi -l`.
- R5. Żadna zmiana nie dotyka `pacer/export.py`, `pacer/sysex.py`,
  `pacer/constants.py` (generowanie bajtów `.syx`) — to jest osobny, już
  sprawdzony kontrakt (bajt-po-bajcie testy w `tests/test_pacer_export.py`).

## Scope Boundaries

- **launchd-owy odpowiednik `deploy/paternologia.service`** (auto-restart,
  start przy logowaniu, watchdog) — decyzja użytkownika: poza zakresem, to
  zadanie dev/lokalne, nie sceniczne wdrożenie na macOS.
- **`pacer_input_subscribed()` / `aconnect`-based replug-detekcja**
  (`midi/ports.py:69-108`, `midi/listener.py`) — mechanizm Linux-only,
  **nie dotykamy go**. Już dziś fail-open (zawsze `True`, gdy `aconnect`
  nie istnieje — patrz `midi/ports.py:81-96`), więc na macOS bezpiecznie
  degraduje precyzję detekcji replugu bez crasha. Realna weryfikacja repluga
  Pacera na macOS pozostaje do ręcznego sprawdzenia na scenie/w praktyce,
  nie do zakodowania w tym planie.
- **Switch A Pacera / jednonutowy toggle nagrywania**
  (`docs/plans/2026-09-10-001-feat-pacer-switch-a-and-record-toggle-plan.md`) —
  niezależny, równoległy plan; nie dotyczy platformy.
- **snd-virmidi / modprobe setup** (README linie 39-51) — Linux-only krok
  instalacyjny, zostaje jako Linux-only (macOS go po prostu nie potrzebuje —
  patrz Overview).

### Deferred to Separate Tasks

- Weryfikacja na fizycznym Pacerze podłączonym do scenicznego Linuksa
  (regresja `amidi` → natywny sender) — wymaga dostępu do sprzętu, nie da się
  wykonać w tej sesji; opisana jako wymagany krok Verification w U1/U2, nie
  jako zamknięty test automatyczny.
- Automatyczny readback-verify (SET→GET→porównanie) przy każdej realnej
  wysyłce, wykorzystujący `pacer/constants.py::CMD_GET` — świadomie poza
  zakresem tego planu (patrz Key Technical Decisions). Warunkowe osobne
  zadanie hardening, tylko jeśli manualna weryfikacja na scenicznym
  Linuksie (patrz wyżej) faktycznie wykaże utracone bajty — wtedy warto
  zbadać, czy firmware Pacera odpowiada na `CMD_GET` dla każdego
  Object/Element z eksportu presetu, jako osobny research przed
  implementacją.

## Context & Research

### Relevant Code and Patterns

- `midi/ports.py::find_rtmidi_output_port(name_substring)` — już generyczne,
  cross-platform wyszukiwanie portu wyjściowego rtmidi po fragmencie nazwy;
  używane dziś przez `midi/bridge.py` do szukania `VirMIDI`. Ten sam wzorzec
  nadaje się bez zmian do szukania portu Pacera po `device_name`.
- `midi/bridge.py::MidiBridge.open/send/close` — wzorzec open→send_message→
  close_port+delete na `rtmidi.MidiOut`, z komentarzem o konieczności
  `delete()` (nie samo `del`) żeby nie wyciekać uchwytu ALSA seq / CoreMIDI
  client. Ten sam wzorzec cyklu życia obowiązuje w nowym senderze.
- `tests/test_midi_ports.py::TestFindRtmidiOutputPort` — wzorzec testowania
  rtmidi przez podstawienie fake klasy `rtmidi.MidiOut` (monkeypatch), bez
  realnego urządzenia. Ten sam wzorzec do użycia w testach nowego sendera.
- `pacer/sysex.py`, `pacer/constants.py` (`SYSEX_START = 0xF0`,
  `SYSEX_END = 0xF7`) — format ramek, potrzebny do napisania parsera blobu
  `.syx` na pojedyncze wiadomości. Sprawdzone: `pacer/sysex.py` i
  `pacer/export.py` tylko *budują* i konkatenują ramki (`b"".join`), nigdy
  nie skanują wstecz granic `0xF0`/`0xF7` — nowy parser w Unit 1 nie
  duplikuje żadnego istniejącego helpera.
- `main.py:132` (`MidiBridge` tworzony raz przy starcie, żyje przez cały
  proces, trwały wirtualny port) vs. planowany sender (one-shot: otwórz→
  paced burst→zamknij, w ramach jednego requestu) — różne cykle życia i
  różna semantyka portu (wirtualny nadawany port vs. wyszukiwany fizyczny
  port Pacera), stąd osobny moduł `midi/sysex_sender.py`, nie metoda na
  `MidiBridge`.

### Institutional Learnings

- `docs/solutions/2026-06-02-bitwig-alsa-seq-invisible-virmidi-bridge.md` —
  potwierdza, że problem "Bitwig nie widzi wirtualnych portów ALSA seq" jest
  Linux/ALSA-specific; nie ma powodu sądzić, że analogiczny problem istnieje
  na macOS/CoreMIDI (tam wirtualne porty są widoczne bezpośrednio).

### External References

- RtMidi C++ source (`github.com/thestk/rtmidi/blob/master/RtMidi.cpp`,
  `MidiOutAlsa`/`MidiOutCore::sendMessage`) i `thestk/rtmidi` issue #214 —
  `send_message()` nie blokuje do dostarczenia na ALSA-sequencer ani CoreMIDI;
  ALSA-sequencer backend ma udokumentowany silent-drop SysEx pod obciążeniem.
- python-rtmidi API docs (`spotlightkid.github.io/python-rtmidi/rtmidi.html`) —
  `send_message()` przyjmuje pełną ramkę `0xF0...0xF7` w jednym wywołaniu,
  bez sprawdzania obecności `0xF7`; brak API do potwierdzenia dostarczenia —
  pacing przez `time.sleep()` między wywołaniami jest jedyną dostępną opcją,
  tak jak dziś robi to `amidi --sysex-interval`.
- `alsa-utils` `amidi.c`/`amidi.1` — `--sysex-interval` jest paced **per
  wiadomość** (po napotkaniu `0xF7`), nie per bajt — potwierdza, że plan
  odtworzenia tego przez `sleep()` **między** kolejnymi `send_message()`
  (po każdej ramce oprócz ostatniej) jest wiernym odtworzeniem semantyki,
  nie uproszczeniem.

## Key Technical Decisions

- **Jeden natywny sender (`python-rtmidi`) dla obu platform, `amidi` usunięty
  całkowicie — decyzja warunkowa, nie bezwarunkowa.** Decyzja użytkownika
  (2026-09-18): jedna ścieżka kodu, mniej duplikacji, mniej rozjazdu
  zachowania między platformami, koszt wdrożenia niski (rtmidi już jest
  zależnością). Alternatywa (natywny sender tylko na macOS, `amidi` bez
  zmian na Linuksie) była rozważona i odrzucona na rzecz tej jednej ścieżki.
  **Cena tej decyzji, nazwana wprost:** oddajemy dowodowo działającą na
  scenie ścieżkę `amidi`/ALSA rawmidi (blokujący `write()`) za code
  simplicity, na rzecz ścieżki nieprzetestowanej na tym konkretnym sprzęcie
  i z udokumentowanym upstream ryzykiem silnego od `amidi` (ALSA sequencer
  silent-drop, `thestk/rtmidi#214` — patrz Risks). Akceptacja tej decyzji
  jest więc **warunkowa na wyniku obowiązkowej weryfikacji sprzętowej na
  scenicznym Linuksie** (Unit 2 Verification — bramka kill, patrz niżej) —
  nie jest zamknięta samym napisaniem kodu. Jeśli ta weryfikacja wykaże
  utratę bajtów na Linuksie, patrz plan B w Risks & Dependencies (rollback
  do `amidi` na Linuksie, natywny sender zostaje tylko na macOS).
  **Ziarno commitów, żeby rollback był realny, nie retoryczny (znalezisko
  review — adversarial/product-lens):** Unit 1 i Unit 2 lądują jako
  commit(y) odrębne od Unit 3/4/5. Cofnięcie Unit 2 (`git revert`)
  przywraca `subprocess`+`amidi` w `routers/pacer.py` natychmiast — **ale
  tylko pod warunkiem, że Unit 3/4/5 (usunięcie pola configu,
  `find_amidi_port`, dokumentacji) jeszcze nie wykonano**. Stąd Unit 3/4/5
  mają wprost w Dependencies wymóg przejścia bramki, nie tylko numer
  poprzedniej jednostki — inaczej "obowiązkowa" jest retoryką, nie
  mechanizmem (patrz Unit 2 Verification, Unit 3/4/5 Dependencies).
  **Uwaga z review (adversarial, present — do jawnej decyzji, nie
  autofix):** przy dev-only scope tego planu i słabości jednorazowego
  testu wobec błędu zależnego od obciążenia (patrz Unit 2 Verification),
  rozważ alternatywę "natywny sender tylko na macOS teraz, unifikacja
  Linuksa jako osobna, późniejsza decyzja po realnym użyciu" — bezpieczniej
  dla stated goal (macOS dev/local), zero ryzyka dla scenicznego Linuksa
  do czasu tej późniejszej decyzji. Decyzja użytkownika z 2026-09-18
  (jeden sender) **stoi**, warunkowo na bramce — ale ta alternatywa
  zostaje tu nazwana wprost, żeby nie zniknęła po jednej rundzie review.
- **Automatyczny readback-verify (`CMD_GET`) po każdej wysyłce — świadomie
  odrzucony z zakresu tego planu.** Protokół Pacera wspiera odczyt stanu
  (`constants.py::CMD_GET = 0x02`), co teoretycznie pozwoliłoby zamienić
  "wyślij i ufaj" na "wyślij i potwierdź" przy każdej realnej wysyłce, nie
  tylko przy jednorazowym teście. Odrzucone, bo: (1) wymagałoby osobnego
  external research — czy firmware Pacera faktycznie odpowiada na `CMD_GET`
  dla każdego Object/Element używanego w eksporcie presetu — czyli
  powtórzyłoby dokładnie ten błąd (niezbadane zachowanie sprzętu), któremu
  plan świadomie zapobiega przy SET; (2) podwaja koszt runtime (SET+GET+
  porównanie) na zawsze, nie tylko przy weryfikacji; (3) to hardening klasy
  "gotowość sceniczna", a Scope Boundaries tego planu explicite ogranicza
  się do dev/local. `CMD_GET` zostaje użyty tylko jednorazowo/manualnie w
  Unit 1/2 Verification (przez pacer-editor, nie kod produkcyjny) — patrz
  też Deferred to Separate Tasks.
- **Pacing: `time.sleep(interval_ms / 1000)` między kolejnymi
  `send_message()`, po każdej kompletnej ramce SysEx oprócz ostatniej** —
  odtwarza dokładnie semantykę `amidi --sysex-interval` (per-wiadomość, nie
  per-bajt), wartość domyślna 20ms zostaje niezmieniona (zwalidowana na
  samym Pacerze, nie na wewnętrznych mechanizmach ALSA/amidi).
- **Bez tymczasowego pliku `.syx`** — dzisiejszy `NamedTemporaryFile` istnieje
  tylko, bo `amidi -s` wymaga pliku na dysku; natywny sender operuje na
  `bytes` w pamięci (te same bajty, które dziś idą do pliku), więc `U2` usuwa
  ten krok jako martwy po zmianie transportu.
- **`amidi_timeout_seconds` (PacerConfig) usunięty, nie repurpose'owany** —
  pole miało sens tylko jako timeout dla `subprocess.run()`; natywna wysyłka
  jest synchroniczna i krótka (brak procesu do timeoutowania), sztuczny
  "timeout" bez realnego mechanizmu odwołania byłby fałszywym bezpieczeństwem.

## Open Questions

### Resolved During Planning

- **Jeden sender czy dwie ścieżki (Linux `amidi` + macOS natywny)?**
  Jeden natywny sender dla obu platform (patrz Key Technical Decisions).
- **Zakres wsparcia macOS: dev czy pełna gotowość sceniczna?** Tylko
  dev/lokalna praca — bez launchd-owego odpowiednika systemd (patrz Scope
  Boundaries).
- **Czy `pacer_input_subscribed`/`aconnect` wymaga zmian dla macOS?** Nie —
  już fail-open, bezpieczny no-op poza Linuksem, poza zakresem tego planu.

### Deferred to Implementation

- Czy `templates/song.html:69-73` ("Usage instructions": `amidi -l`,
  `amidi -p ... --sysex-interval=20 -s ...`) jest gdzieś jeszcze
  odnośnikowany/testowany poza samym HTML, i czym dokładnie zastąpić treść
  tej sekcji tak, by nie zasugerować "użyj rtmidi ręcznie" — to nie jest
  realna opcja dla użytkownika końcowego bez napisania własnego skryptu —
  do ustalenia przy edycji U5 (patrz Unit 5 Approach: pacer-editor jako
  platform-agnostic manualna opcja obok przycisku "Download .syx").
- Dokładny kontrakt błędu nowego sendera (wyjątek własnej klasy vs `None`
  return z funkcji lookup + wyjątek tylko z `rtmidi` przy realnym I/O) — do
  ustalenia przy pisaniu pierwszego testu w U1, tak by `routers/pacer.py`
  (U2) mapował go 1:1 na dzisiejsze kody HTTP 400/500.
- Czy Pydantic `PacerConfig` (brak explicit `model_config` w `models.py`)
  domyślnie ignoruje nieznane pola z YAML, czy rzuca błąd walidacji — wpływa
  na to, czy usunięcie `amidi_timeout_seconds` z modelu (U3) wymaga
  jednoczesnej edycji `data/pacer.yaml`, czy edycja YAML może poczekać.
  Zalecane: zrobić obie zmiany w tym samym commicie niezależnie od odpowiedzi.

## Implementation Units

- [ ] **Unit 1: Natywny cross-platform SysEx sender**

**Goal:** Nowy moduł zastępujący `amidi -s` — parsuje blob `.syx` na pojedyncze
ramki i wysyła je przez `python-rtmidi` z zachowanym pacingiem, identycznie na
Linuksie i macOS.

**Requirements:** R1, R2, R5

**Dependencies:** Brak (nowy, izolowany moduł)

**Files:**
- Create: `packages/paternologia/src/paternologia/midi/sysex_sender.py`
- Test: `packages/paternologia/tests/test_sysex_sender.py`

**Approach:**
- Funkcja `split_sysex_messages(data: bytes) -> list[bytes]`: skanuje blob,
  wycina kolejne ramki `0xF0 ... 0xF7` (identyczny format jak generuje
  `pacer/sysex.py`).
- Funkcja/klasa wysyłająca: znajduje port wyjściowy przez istniejące
  `midi/ports.py::find_rtmidi_output_port(device_name)` (bez zmian w tej
  funkcji — już generyczna), otwiera `rtmidi.MidiOut`, iteruje ramki z
  `split_sysex_messages`, `send_message(list(frame))`, a między kolejnymi
  wysyłkami (po każdej ramce **oprócz ostatniej**) —
  `time.sleep(interval_ms / 1000)`; zawsze zwalnia port
  (`close_port()` + `delete()`) w `finally` — nawet po wyjątku w połowie
  wysyłki (wzorzec z `MidiBridge.close()`).
- Zachowuje dzisiejsze **pierwsze dopasowanie po nazwie** — ta sama
  niejednoznaczność MIDI1 vs MIDI2, co dziś w `find_amidi_port` +
  `amidi -l` (nie jest to nowy problem wprowadzony tym planem).

**Execution note:** Test-first (reguła projektu, `AGENTS.md`) — zacznij od
testu `split_sysex_messages` na realnym blobie z `export_song_to_syx()`
(fixture z `tests/test_pacer_export.py`), potem testu pacingu z mockiem
`time.sleep`.

**Patterns to follow:**
- `midi/bridge.py::MidiBridge` (cykl życia `rtmidi.MidiOut`)
- `midi/ports.py::find_rtmidi_output_port`
- `tests/test_midi_ports.py::TestFindRtmidiOutputPort` (fake `rtmidi.MidiOut`)

**Test scenarios:**
- Happy path: blob z 3 ramkami → sender wysyła 3× `send_message()` z bajtami
  identycznymi co wejściowe ramki, w kolejności, ze snem między nimi (2 sny
  dla 3 ramek, nie 3, nie 0)
- Happy path: `split_sysex_messages(export_song_to_syx(...))` zwraca tyle
  ramek, ile `export.py` faktycznie zbudował (regresja na istniejącym
  kontrakcie generowania)
- Edge case: pusty blob → zero ramek, sender nie otwiera portu
- Edge case: blob z ostatnią ramką bez `0xF7` (obcięty plik) → czytelny
  błąd, żadna częściowa/uszkodzona ramka nie trafia do `send_message()`
- Error path: `find_rtmidi_output_port` zwraca `None` (urządzenie
  niepodłączone) → sender sygnalizuje błąd bez próby `rtmidi.MidiOut()`
- Error path: `open_port()` lub `send_message()` rzuca w połowie wysyłki
  (np. urządzenie odłączone w trakcie) → wyjątek propagowany czytelnie,
  port zawsze zwolniony w `finally` (asercja na `close_port`+`delete`
  wywołane nawet po wyjątku)

**Verification:**
- Testy jednostkowe zielone z mockowanym `rtmidi`.
- Wstępna wysyłka realnego presetu do fizycznego Pacera na macOS (dev) —
  sanity check modułu w izolacji. **Pełna bramka kill (obowiązkowa,
  Linux)** jest w Unit 2 Verification, nie tutaj — sender sam nie ma
  konsumenta HTTP do end-to-end testu.

---

- [ ] **Unit 2: `routers/pacer.py` przechodzi na natywny sender**

**Goal:** `POST /pacer/send/{song_id}` używa `sysex_sender` z Unit 1 zamiast
`subprocess`+`amidi`+plik tymczasowy.

**Requirements:** R1, R3

**Dependencies:** Unit 1

**Files:**
- Modify: `packages/paternologia/src/paternologia/routers/pacer.py`
- Test: `packages/paternologia/tests/test_api.py` (`TestPacerSendEndpoint`)

**Approach:**
- Usuń `import subprocess`, `from tempfile import NamedTemporaryFile`,
  `find_amidi_port` — `syx_data` (już `bytes` z `export_song_to_syx`) idzie
  wprost do sendera, bez pliku na dysku.
- Usuń też linię `timeout_seconds = pacer_config.amidi_timeout_seconds`
  (dziś `routers/pacer.py:103`) — martwa po usunięciu `subprocess.run(...,
  timeout=timeout_seconds, ...)`; inaczej Unit 3 (usuwa pole z modelu)
  zostawia tu `AttributeError` w runtime (znalezisko coherence-review).
- Pole `port` w odpowiedzi JSON/HTMX (`{"status": "ok", ..., "port": port}`)
  zmienia format: dziś ALSA `hw:X,Y,Z`, po zmianie — nazwa portu rtmidi
  (np. `"PACER MIDI1"`). To zamierzona zmiana, nie regresja — pole jest
  informacyjne (span tekstowy w UI), ale zweryfikuj w wykonaniu, czy nic
  poza tym nie parsuje `hw:` (patrz Deferred to Implementation).
- Mapowanie błędów sendera na dzisiejsze kody HTTP: port nie znaleziony →
  400 "Nie znaleziono ... (device_name)"; wyjątek w trakcie wysyłki → 500 z
  treścią błędu (analogicznie do dzisiejszych "amidi not found"/"amidi
  failed", ale bez odwołań do `amidi` w treści komunikatu).

**Patterns to follow:**
- Istniejąca struktura `send_to_pacer()` (walidacja song → preset → config →
  port → export → wysyłka → odpowiedź HTMX/JSON) zostaje, zmienia się tylko
  krok "port" i "wysyłka".

**Test scenarios:**
- Happy path: sukces wysyłki, domyślny preset `A1`, `port` w odpowiedzi =
  nazwa znalezionego portu rtmidi (regresja zachowania, nowy format pola)
- Happy path: custom preset override (`B3`) (regresja, bez zmian logiki)
- Happy path: domyślny preset z `song.pacer_export.target_preset` (regresja)
- Error path: song not found → 404 (regresja, bez zmian)
- Error path: brak `data/pacer.yaml` → 400 (regresja, bez zmian)
- Error path: invalid preset → 400 (regresja, bez zmian)
- Error path: port nie znaleziony → 400 "Nie znaleziono" (dziś:
  `find_amidi_port` → `None`; po zmianie: sender/`find_rtmidi_output_port`
  → `None`, ten sam komunikat)
- Error path: sender rzuca w trakcie wysyłki → 500 z czytelnym komunikatem
  (zamienia dzisiejsze `amidi not found`/`amidi failed`)
- Integration: router przekazuje do sendera `device_name` i
  `sysex_interval_ms` **wprost z `PacerConfig`, bez modyfikacji** — asercja
  na `call_args` wywołania sendera (wzorzec z dzisiejszego
  `mock_run.call_args[0][0]` w `test_send_to_pacer_success`, przeniesiony na
  nową granicę kolaboratora). To realna dziura w dzisiejszych testach:
  `sysex_interval_ms` nie jest asertowany nigdzie w obecnym
  `test_api.py` — sama zmiana konfiguracji (np. przez operatora edytującego
  `pacer.yaml`) mogłaby się dziś silently nie propagować i żaden test by
  tego nie złapał

**Verification (bramka kill):** `uv run --package paternologia pytest -k
pacer_send` zielone ORAZ **wielokrotna** (nie jednorazowa — silent-drop
ALSA-sequencer jest zależny od obciążenia/timingu, nie deterministyczny,
patrz Problem Frame) realna wysyłka presetu z endpointu do fizycznego
Pacera **na scenicznym Linuksie, pod realnym obciążeniem systemu (OBS +
Bitwig + paternologia razem, jak na żywym secie)**, z porównaniem
odczytu w pacer-editorze po każdej próbie. **Kill →** decyzja "jeden
sender" jest odwołana dla Linuksa: `git revert` commit(a/ów) Unit 1+2 —
działa czysto tylko jeśli Unit 3/4/5 jeszcze nie wykonane (patrz Key
Technical Decisions, ziarno commitów). Natywny sender zostaje jedyną
ścieżką tylko na macOS; Linux wraca do `amidi`.

**STATUS: PENDING** — wymaga dostępu do scenicznego Linuksa, niewykonalne
w tej sesji (patrz Scope Boundaries → Deferred to Separate Tasks). **Unit
3, Unit 4 i Unit 5 nie zaczynają się przed wpisaniem tu `STATUS: PASS`** —
to jest literalna bramka w ich Dependencies, nie tylko zalecenie.

---

- [ ] **Unit 3: Porządek `PacerConfig` i `data/pacer.yaml` po usunięciu `amidi`**

**Goal:** Usuń pole `amidi_timeout_seconds` (bez sensu bez `subprocess`),
zaktualizuj opisy pól odwołujące się do `amidi -l`.

**Requirements:** R3, R4

**Dependencies:** Unit 1, Unit 2 **z `STATUS: PASS` w Unit 2 Verification
(bramka kill)** — nie tylko numer jednostki (patrz Key Technical Decisions,
ziarno commitów: dopóki bramka nie przejdzie, rollback Unit 1+2 musi
zostać czysty, a to wymaga, żeby Unit 3 jeszcze nie ruszał pola configu).

**Files:**
- Modify: `packages/paternologia/src/paternologia/models.py`
- Modify: `packages/paternologia/data/pacer.yaml`
- Modify: `packages/paternologia/tests/test_models.py`
  (`TestPacerConfig`: `test_default_device_name`, `test_custom_timeout`,
  `test_timeout_min_value`, `test_timeout_max_value` — konstruują/asertują
  `amidi_timeout_seconds`, padną po usunięciu pola z modelu)
- Modify: `packages/paternologia/tests/test_storage.py`
  (`TestPacerConfigStorage`: `test_save_and_get_pacer_config`,
  `test_get_pacer_config_with_default_timeout` — to samo)

**Approach:**
- Usuń `amidi_timeout_seconds: int = Field(...)` z `PacerConfig`.
- Zaktualizuj `description=` pola `device_name` ("szukana w amidi -l" →
  neutralny opis wykrywania po nazwie portu MIDI).
- Usuń wiersz `amidi_timeout_seconds: 5` i komentarz `# Sprawdź dostępne
  urządzenia: amidi -l` z `data/pacer.yaml`; zaktualizuj nagłówkowy komentarz
  pliku (dziś: "Konfiguracja portu amidi dla Nektar Pacer").
- Usuń/zaktualizuj asercje i argumenty konstruktora `amidi_timeout_seconds`
  we wskazanych testach `test_models.py`/`test_storage.py` — inaczej Unit 4
  (`pytest zielone w całości`) pada z przyczyny wprowadzonej tu, nie tam
  (znalezisko feasibility-review).

**Test scenarios:**
- Happy path: `data/pacer.yaml` (po edycji) wczytuje się bez błędu walidacji
  (regresja na realnym pliku konfiguracyjnym, nie fixture)
- Test expectation: none dla samej zmiany treści `description=` — kosmetyka,
  nie zachowanie.

**Verification:**
- `grep -rn amidi_timeout_seconds packages/paternologia/src
  packages/paternologia/tests packages/paternologia/data` zwraca zero
  wyników (rozszerzony zakres — patrz Files).
- Storage layer wczytuje `PacerConfig` z produkcyjnego `data/pacer.yaml` bez
  wyjątku (istniejący test storage, jeśli pokrywa `get_pacer_config`).

---

- [ ] **Unit 4: Usunięcie martwego kodu `find_amidi_port`**

**Goal:** Po Unit 2 `find_amidi_port` nie ma już żadnego wołającego — usuń
funkcję i jej testy.

**Requirements:** R1

**Dependencies:** Unit 2 **z `STATUS: PASS` w Unit 2 Verification (bramka
kill)** — patrz Unit 3 Dependencies, ten sam powód.

**Files:**
- Modify: `packages/paternologia/src/paternologia/midi/ports.py`
  (usuń `find_amidi_port`)
- Modify: `packages/paternologia/tests/test_midi_ports.py`
  (usuń klasę `TestFindAmidiPort`)

**Approach:**
- `pacer_input_subscribed()` (ten sam plik, `aconnect`-based) **zostaje bez
  zmian** — inny mechanizm (replug-detekcja dla `MidiListener`), poza
  zakresem tego planu (patrz Scope Boundaries).

**Test scenarios:**
- Test expectation: none — czyste usunięcie martwego kodu; pozostałe klasy
  w `test_midi_ports.py` (`TestPacerInputSubscribed`, `TestFindRtmidiPorts`,
  `TestFindRtmidiOutputPort`) przechodzą bez zmian (regresja).

**Verification:**
- `grep -rn find_amidi_port packages/paternologia/src` zwraca zero wyników.
- `uv run --package paternologia pytest` zielone w całości.

---

- [ ] **Unit 5: Dokumentacja i UI-instrukcje**

**Goal:** README, `pacer.yaml`, `SPEC_PACER_BRIDGE.md` i "Usage instructions"
w UI przestają zakładać Linuksa/`amidi` jako jedynej opcji.

**Requirements:** R4

**Dependencies:** Unit 1, Unit 2 **z `STATUS: PASS` w Unit 2 Verification
(bramka kill)**, Unit 3 — ten sam powód co Unit 3/4 (dokumentacja mówiąca
"amidi już nie istnieje" musi zostać prawdziwa, nie wyprzedzać bramki).

**Files:**
- Modify: `packages/paternologia/README.md`
- Modify: `packages/paternologia/templates/song.html`
- Modify: `packages/paternologia/SPEC_PACER_BRIDGE.md`
- Modify: `packages/paternologia/SPEC_PACER_EXPORT_v2.md` (6 odwołań do
  `amidi`, w tym identyczny blok "Usage instructions" co w
  `templates/song.html` — README go wymienia jako równorzędny kanoniczny
  spec obok `SPEC_PACER_BRIDGE.md`, więc R4 nie jest spełnione bez niego;
  znalezisko feasibility-review)

**Approach:**
- README: usuń `amidi` z listy wymaganych zewnętrznych narzędzi (linia 9);
  zaktualizuj opis "Bezpośrednia wysyłka" (linia 133) — teraz natywnie przez
  `python-rtmidi`, bez zewnętrznej zależności, na obu platformach; dodaj
  krótką notkę, że bridge do Bitwiga na macOS to zwykły widoczny wprost port
  CoreMIDI `setka-bridge` (bez odpowiednika `snd-virmidi`/`modprobe`, które
  zostają jako Linux-only krok instalacyjny, opisany jako taki).
- `templates/song.html:67-74` ("Usage instructions"): usuń
  `amidi -l`/`amidi -p ... -s ...` jako instrukcję ręczną — przycisk "Wyślij
  do Pacer" już to robi natywnie na obu platformach; jeśli sekcja ma
  zostać jako fallback dla `.syx` z "Download", zaktualizuj ją tak by nie
  odsyłała do nieistniejącego na macOS binarki (np. wskazać pacer-editor
  jako platform-agnostic manualną opcję).
- `SPEC_PACER_BRIDGE.md` i `SPEC_PACER_EXPORT_v2.md`: to dokumenty
  historyczne — dopisz krótką notkę na końcu każdego odsyłającą do tego
  planu, nie przepisuj narracji "Spec 1 vs Spec 2" ani reszty treści.

**Test scenarios:**
- Test expectation: none — dokumentacja i statyczny HTML, brak zachowania
  do testowania.

**Verification:**
- `grep -rln amidi packages/paternologia/README.md
  packages/paternologia/templates/song.html
  packages/paternologia/SPEC_PACER_EXPORT_v2.md
  packages/paternologia/data/pacer.yaml` zwraca zero wyników (poza
  historyczną notką w `SPEC_PACER_BRIDGE.md`/`SPEC_PACER_EXPORT_v2.md`,
  które celowo wspominają `amidi` jako przeszłość).

## System-Wide Impact

- **Interaction graph:** `routers/pacer.py::send_to_pacer` jest jedynym
  konsumentem `find_amidi_port`/`amidi`. `midi/listener.py` i `midi/bridge.py`
  (replug-detekcja, fan-out do Bitwiga) używają innego, już cross-platform
  mechanizmu (`rtmidi` bezpośrednio) i nie są dotknięte tym planem.
- **Error propagation:** błędy nowego sendera muszą trafiać do tego samego
  400/500 kontraktu HTTP co dziś, żeby istniejący HTMX error-handling w UI
  (`#send-result` span z klasą `text-red-600`) nie się zepsuł.
- **State lifecycle risks:** `rtmidi.MidiOut` w senderze musi być zawsze
  zamknięty (`close_port()`+`delete()`) nawet przy wyjątku w połowie
  wysyłki wielu ramek — inaczej wyciek uchwytu ALSA-seq/CoreMIDI client przy
  każdej nieudanej wysyłce (ten sam wzorzec ryzyka, co komentarz w
  `MidiBridge.close()` już dokumentuje).
- **API surface parity:** pole `port` w odpowiedzi `POST /pacer/send/{song_id}`
  zmienia format (`hw:X,Y,Z` → nazwa portu rtmidi) — sprawdź w wykonaniu, czy
  coś poza samym UI parsuje ten format.
- **Unchanged invariants:** `pacer/export.py`, `pacer/sysex.py`,
  `pacer/constants.py` (generowanie bajtów `.syx`) i `GET
  /pacer/export/{song_id}.syx` (plain download) — całkowicie nietknięte;
  `midi/listener.py` replug-detekcja i `pacer_input_subscribed`/`aconnect` —
  bez zmian.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Backend ALSA-sequencer, który `python-rtmidi` używa na Linuksie, ma udokumentowany (`thestk/rtmidi#214`) silent-drop SysEx pod obciążeniem, zależny od timingu/obciążenia (nie deterministyczny) — inny mechanizm niż dzisiejszy `amidi` (rawmidi, blokujący `write()`); natywny sender może być na Linuksie *mniej* pewny niż `amidi`, nie tylko "równie dobry" | Zachowany identyczny pacing 20ms/ramkę; **bramka kill w Unit 2 Verification** (nie tylko deklaracja "obowiązkowa" w prozie) — wielokrotna wysyłka pod realnym obciążeniem systemu na scenicznym Linuksie, `STATUS: PENDING` do wykonania na sprzęcie. **Unit 3/4/5 mają ten `STATUS: PASS` wpisany literalnie w swoich Dependencies** — nie mogą się zacząć przed nim, więc rollback (`git revert` Unit 1+2) zostaje czysty tak długo, jak bramka nie przejdzie. Patrz Deferred to Separate Tasks |
| Zmiana formatu pola `port` w odpowiedzi API (`hw:X,Y,Z` → nazwa rtmidi) może łamać nieoczekiwany downstream parser | Grep szablonów/JS w wykonaniu (Unit 2); pole jest dziś czysto informacyjne (tekst w UI), ryzyko niskie |
| Usunięcie `amidi_timeout_seconds` to zmiana schematu `data/pacer.yaml` | Jeden plik, ręczna edycja w tym samym commicie co zmiana modelu (Unit 3), nie migracja danych |
| Brak fizycznego Pacera w środowisku deweloperskim/CI — nie da się w pełni zweryfikować pacingu i braku utraty bajtów bez sprzętu | Testy jednostkowe mockują `rtmidi`/`time.sleep` (Unit 1); realna weryfikacja świadomie odłożona do wykonania na sprzęcie, nie udawana jako "gotowe" po zielonych testach jednostkowych |

## Sources & References

- Related code: `packages/paternologia/src/paternologia/routers/pacer.py`,
  `packages/paternologia/src/paternologia/midi/ports.py`,
  `packages/paternologia/src/paternologia/midi/bridge.py`,
  `packages/paternologia/src/paternologia/midi/listener.py`
- Historyczna decyzja `amidi` vs `python-rtmidi`:
  `packages/paternologia/SPEC_PACER_BRIDGE.md` (sekcja 8-9)
- Institutional learning: `docs/solutions/2026-06-02-bitwig-alsa-seq-invisible-virmidi-bridge.md`
- External: RtMidi C++ source (`github.com/thestk/rtmidi`), issue #214;
  python-rtmidi API docs (`spotlightkid.github.io/python-rtmidi`);
  `alsa-utils` `amidi.c`/`amidi.1`
