---
title: "feat: Orkiestracja uruchamiania środowiska live (OBS + Bitwig + kiosk paternologii)"
type: feat
status: completed
date: 2026-06-02
deepened: 2026-06-02
---

# feat: Orkiestracja uruchamiania środowiska live (OBS + Bitwig + kiosk paternologii)

## Overview

Wprowadzamy systemd `--user` target (`live-recording.target`), który jedną komendą stawia
komplet do nagrywania live: OBS Studio, Bitwig Studio (flatpak) i okno przeglądarki z
widokiem `/live` paternologii — we właściwej kolejności, po sprawdzeniu, że zależności
(virmidi, PipeWire 44100, żywa paternologia) są gotowe. Druga komenda robi całościowy,
deterministyczny restart całej warstwy GUI.

paternologia (`paternologia.service`) zostaje **bez zmian funkcjonalnych** jako stale
żywy MIDI bridge z watchdogiem — target od niej zależy, ale jej nie restartuje (restart
mostu zerwałby fan-out PACER w trakcie występu, a link most→virmidi i tak wraca sam).

## Problem Frame

Dziś paternologia żyje jako usługa, a kiosk UI startuje przez XDG autostart przy każdym
logowaniu. **OBS i Bitwig odpalasz ręcznie**, w ręcznej kolejności, bez weryfikacji że
audio/MIDI są gotowe. Nie istnieje też jedna komenda do całościowego restartu, gdy coś
się rozjedzie podczas przygotowań do nagrania. Cele Wojtasa:

- a) jednym zamachem postawić gotowe środowisko live;
- b) przy potrzebie zrestartować je całościowo.

## Requirements Trace

- R1. Jedna komenda startuje komplet OBS + Bitwig + kiosk paternologii (cel a).
- R2. Start respektuje twarde zależności kolejnościowe: `snd-virmidi` załadowany, PipeWire
  na 44100, paternologia `/health` zielona — **zanim** wstanie Bitwig/OBS/kiosk.
- R3. Jedna komenda robi całościowy restart warstwy GUI, omijając znaną pułapkę
  „restart targetu nie restartuje członków" (cel b).
- R4. OBS i Bitwig **bez** auto-restartu — crash nie jest po cichu wznawiany (ochrona
  pliku nagrania OBS i stanu sesji Bitwiga). Decyzja operatora, nie automatu.
- R5. Tryb **na żądanie**: komplet startuje gdy siadasz do nagrywania, nie przy każdym
  zalogowaniu. Obecny kiosk-autostart przy logowaniu zostaje wycofany na rzecz tego trybu.
- R6. Unity i skrypty są wersjonowane w repo i instalowalne jedną komendą (jak istniejące
  `packages/paternologia/deploy/paternologia.service`).

## Scope Boundaries

- **Nie** zarządzamy cyklem życia `paternologia.service` z poziomu targetu (zostaje
  osobno, z watchdogiem). Target tylko od niej *zależy* przez ordering + preflight.
- **Nie** automatyzujemy „Restart Audio Engine" w Bitwigu (nieautomatyzowalne — wymaga
  ręcznej akcji w UI po replug/restart PipeWire; patrz `docs/solutions`).
- **Nie** ruszamy konfiguracji PipeWire 44100 ani persystencji `snd-virmidi` (już
  zrobione i utrwalone) — preflight je tylko *weryfikuje*, nie ustawia.
- **Nie** zmieniamy logiki MIDI/OBS-websocket paternologii.
- **OBS i Bitwig są niezależne urządzeniowo** (OBS = kamery/wideo, Bitwig = RC-600/interfejs
  audio) — nie współdzielą `/dev`, więc startują **równolegle** jako członkowie targetu bez
  ordering między sobą. Brak deterministycznej kolejności OBS↔Bitwig jest zamierzony, nie
  przeoczony.
- **Nie** dotykamy konfiguracji kontrolera w Bitwigu (MIDI Input = „Virtual Raw MIDI 1",
  surowe PACER wyłączone) — to ustawienie jednorazowe, niezależne od kolejności startu.

## Context & Research

### Relevant Code and Patterns

- `packages/paternologia/deploy/paternologia.service` — wzorzec unitu systemd `--user`
  w tym repo (ABOUTME, `%h`, `uv run`, komentarze operatorskie). Nowe unity mają go
  naśladować stylem.
- `~/.config/systemd/user/paternologia.service` — zainstalowana usługa: `Type=notify`,
  `Restart=always`, `WatchdogSec=10`, `After=sound.target pipewire.service`,
  `WantedBy=default.target`, linger włączony.
- `~/.local/bin/paternologia-kiosk.sh` — istniejący skrypt kiosk: poll `http://localhost:8000/`
  (max ~30 s) → `brave --kiosk` z osobnym `--user-data-dir`. Logika pollingu i osobnego
  profilu do zachowania; przenosimy go pod kontrolę systemd i wersjonujemy w repo.
- `~/.config/autostart/paternologia-kiosk.desktop` — XDG autostart, do **wycofania**
  (tryb na żądanie, R5).
- Endpoint `GET /health` paternologii: `pacer_input_open`, `bridge_port_active`,
  `obs_connected`, `last_heartbeat_ts` — podstawa preflight-gatingu.
- `packages/paternologia/data/obs.yaml` — OBS websocket `localhost:4455`; OBS musi mieć
  włączony WebSocket Server (już: `server_enabled: true`).

### Institutional Learnings

- `docs/solutions/2026-06-02-bitwig-alsa-seq-invisible-virmidi-bridge.md`:
  `snd-virmidi` musi być załadowany **zanim** wstanie paternologia i zanim Bitwig
  enumeruje wejścia MIDI; bez modułu most degraduje do niewidzialnego portu seq.
  Strona `hw:Virmidi` trwa niezależnie od paternologii → link most→virmidi wraca sam po
  restarcie usługi (kolejność odporna w tę stronę).
- `docs/solutions/2026-06-01-bitwig-pipewire-44100-usb-audio-contention.md`:
  PipeWire musi mieć graf gotowy na 44100 **zanim** Bitwig otworzy urządzenie (RC-600
  taktowany sprzętowo na 44100). **Nigdy nie restartować PipeWire pod żywym Bitwigiem** —
  wyrywa graf, wiesza silnik audio. To krytyczne ograniczenie dla strategii restartu.
- `docs/plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md` — kontekst usługi
  paternologii (watchdog, linger, stała nazwa portu mostu).

### External References

Best-practices research (systemd `--user` + GUI/flatpak na GNOME, 2025/2026). **Uwaga:**
research zakładał Wayland, ale weryfikacja na maszynie pokazała sesję **X11** — ustalenia
o środowisku graficznym przepisano pod X11 (gating na `DISPLAY`, nie `WAYLAND_DISPLAY`):

- **Pułapka restartu targetu** (potwierdzona w issue trackerze systemd):
  `systemctl --user restart <target>` restartuje tylko pusty target — `Wants`/`Requires`
  to zależności *startu*, nie propagacja *restartu*. Rozwiązanie: `PartOf=` na członkach +
  `stop && start` targetu, albo jawna lista usług w komendzie. Źródła: systemd #13841,
  #24068, #32382.
- **Środowisko graficzne (X11 na tej maszynie)**: `DISPLAY=:1` jest już obecne w activation
  environment systemd usera, więc GUI usługi je dziedziczą bez zabiegów. Bezpiecznik:
  `ConditionEnvironment=DISPLAY`. (Na Wayland byłoby `WAYLAND_DISPLAY` + ewentualny
  `dbus-update-activation-environment --systemd` — nie dotyczy tej maszyny.) Źródła: sway
  wiki, GNOME SessionStart, Arch Wiki UWSM.
- **Flatpak pod systemd**: main PID = `bwrap`, więc `Type=exec`/`simple` (nie `forking`);
  `ExecStop=/usr/bin/flatpak kill com.bitwig.BitwigStudio`; ryzyko ubicia cgroup przed
  ExecStop → potrzebny zapas `TimeoutStopSec`; logi flatpaka bywają nieskojarzone z
  serwisem w journalu. Źródła: flatpak #5870, #3340.
- **KillMode/Timeout**: `KillMode=control-group` (sprzątanie całego drzewa: renderery
  Brave, helpery, bwrap); `TimeoutStopSec` z zapasem, by OBS zdążył domknąć/flush plik a
  Bitwig zapisać sesję (za krótki = SIGKILL = uszkodzone nagranie). Źródła: systemd.kill(5),
  systemd #14566.
- **Preflight**: osobny `Type=oneshot` + `RemainAfterExit=yes`; członkowie GUI z
  `Requires=` + `After=` na nim (tu `Requires` jest właściwe — brak warunku ma **blokować**
  start GUI).

## Key Technical Decisions

- **systemd `--user` target jako szkielet** (wybór Wojtasa): spójny z istniejącą usługą
  paternologii, logi w `journalctl --user`, deklaratywna kolejność przez `After=`.
- **Restart całościowy przez `stop && start` targetu, nie `restart` targetu**: wymusza
  `PartOf=live-recording.target` na każdym członku (żeby `stop` targetu pociągnął ich
  stop), a `Wants=` w targecie odpala ich z powrotem przy `start`. Owijamy w skrypt
  `setka-live`, by operator nie musiał pamiętać o pułapce. (see external: systemd #13841)
- **Preflight jako oneshot gate, nie `ExecStartPre` w każdej usłudze**: jeden
  `live-preflight.service` weryfikuje virmidi + PipeWire 44100 + `/health`; GUI usługi
  `Requires=`+`After=` na nim. DRY — warunek w jednym miejscu, twarda blokada startu GUI
  gdy audio/MIDI nie gotowe.
- **`Restart=no` jawnie na OBS/Bitwig/kiosk** (R4): świadoma polityka, nie brak
  konfiguracji — chroni nagranie i stan sesji; komentarz w unicie tłumaczy dlaczego.
- **`Type=exec` dla GUI**: unit „wystartowany" dopiero po udanym `execve` (lepsza
  diagnostyka niż `simple`); `forking` błędny dla flatpak/Brave/OBS.
- **Środowisko graficzne przez `ConditionEnvironment=DISPLAY`** na członkach. **Sesja na
  tej maszynie to X11, nie Wayland** (zweryfikowane: `XDG_SESSION_TYPE=x11`, `DISPLAY=:1`,
  `WAYLAND_DISPLAY` puste). Co istotne, `DISPLAY=:1` **jest już** w activation environment
  systemd usera (`systemctl --user show-environment` → `DISPLAY=:1`; GNOME/X11 je wypycha),
  więc GUI usługi odziedziczą DISPLAY bez dodatkowych zabiegów, a `ConditionEnvironment=DISPLAY`
  jest realnym, spełnialnym bezpiecznikiem. **NIE** używać `ConditionEnvironment=WAYLAND_DISPLAY`
  — na X11 zablokowałoby po cichu wszystkie usługi GUI.
- **Tryb na żądanie** (R5): `WantedBy=live-recording.target` na członkach (nie
  `graphical-session.target`); target **nie** ma `WantedBy=default.target`, więc nic nie
  wstaje przy logowaniu, dopóki operator nie odpali `setka-live start`. Stary
  `paternologia-kiosk.desktop` wyłączamy.
- **Wersjonowanie w repo**: nowy katalog `deploy/live/` w roocie monorepo (unity +
  skrypty + instalator), analogicznie do `packages/paternologia/deploy/`. Skrypt
  instalacyjny kopiuje do `~/.config/systemd/user/` i `~/.local/bin/`, robi
  `daemon-reload`.

## Open Questions

### Resolved During Planning

- *Mechanizm orkiestracji?* → systemd `--user` target (wybór Wojtasa).
- *Kiedy startuje środowisko?* → na żądanie (wybór Wojtasa); kiosk-autostart wycofany.
- *Auto-restart OBS/Bitwig?* → nie (wybór Wojtasa); tylko paternologia ma watchdog.
- *Jak zrobić działający „całościowy restart"?* → `PartOf=` + `stop && start` targetu w
  skrypcie, bo `restart .target` nie propaguje (potwierdzone w research).
- *Czy restart obejmuje paternologię?* → nie. `setka-live` nigdy nie tyka mostu; rzadki
  restart mostu robi się ręcznie `systemctl --user restart paternologia.service` (flagi
  `--with-bridge` nie dodajemy — YAGNI, decyzja Wojtasa).
- *Preflight: twardy blok czy ostrzeżenie?* → twardy `Requires=` (fail-fast: nie startuj GUI
  bez audio/MIDI), ale z retry/grace w skrypcie dostrojonym pod watchdog paternologii i
  stabilizację PipeWire, by ograniczyć fałszywie-negatywne pojedyncze strzały (decyzja Wojtasa).
- *Czy OBS i Bitwig współdzielą urządzenie USB?* → nie. OBS bierze kamery/wideo, Bitwig
  RC-600/interfejs audio — rozdzielne urządzenia, więc równoległy start członków jest
  bezpieczny i zamierzony (decyzja Wojtasa).
- *Strategia sesji graficznej?* → **X11 na stałe** (decyzja Wojtasa); gating
  `ConditionEnvironment=DISPLAY`, bez obsługi dual X11/Wayland.
- *Czy preflight ma ustawiać PipeWire 44100 / ładować virmidi?* → nie, tylko weryfikuje
  (oba już utrwalone na boot); brak warunku = twardy fail z czytelnym komunikatem.
- *Typ sesji i propagacja środowiska graficznego?* → **X11** (zweryfikowane: `XDG_SESSION_TYPE=x11`,
  `DISPLAY=:1`, `WAYLAND_DISPLAY` puste). `DISPLAY=:1` jest już w activation environment
  systemd usera → GUI dziedziczą je bez `dbus-update-activation-environment`; bezpiecznik to
  `ConditionEnvironment=DISPLAY`.
- *Framework testów skryptów?* → plain `test_*.sh` (zweryfikowane: `bats` nie jest
  zainstalowany; nie wprowadzamy nowej zależności toolingu dla kilku skryptów).
- *Czy preflight weryfikuje `obs_connected`?* → nie. OBS startuje **po** preflighcie, więc
  websocket nie jest jeszcze podniesiony — preflight sprawdza tylko `pacer_input_open &&
  bridge_port_active`. Pełne zdrowie (w tym `obs_connected`) audytuje `setka-live status`.

### Deferred to Implementation

- Dokładny czas `TimeoutStopSec` dla OBS i Bitwiga — dostroić empirycznie tak, by OBS
  flushował plik a Bitwig zapisał sesję (start od OBS 30 s / Bitwig 60 s).
- Dokładna treść komunikatów błędów preflight (mają wskazywać operatorowi co podłączyć).

## High-Level Technical Design

> *Ilustruje zamierzone podejście — kierunkowa wskazówka do review, nie specyfikacja
> implementacji. Agent implementujący traktuje to jako kontekst, nie kod do odtworzenia.*

Graf zależności i kolejności (strzałka = „After / wymaga"):

```
                 [pipewire.service / sound.target]      (systemowe, już są)
                            │
                 paternologia.service  (Type=notify, Restart=always, watchdog — BEZ ZMIAN)
                            │
                 live-preflight.service  (oneshot, RemainAfterExit=yes)
                   ├─ weryfikuje: hw:Virmidi istnieje (lsmod/aplaymidi -l)
                   ├─ weryfikuje: PipeWire clock.rate == 44100 (pw-metadata)
                   └─ weryfikuje: GET /health → pacer_input_open && bridge_port_active
                            │ Requires= + After=
        ┌───────────────────┼───────────────────┐
   obs.service         bitwig.service        kiosk.service
   Type=exec           Type=exec             Type=exec
   /usr/bin/obs        flatpak run …         brave --kiosk /live
   Restart=no          ExecStop=flatpak kill Restart=no
   PartOf=target       PartOf=target         PartOf=target
        └───────────────────┴───────────────────┘
                            │ Wants= (w targecie)
                 live-recording.target   (tryb na żądanie; brak WantedBy=default.target)

Operator (skrypt setka-live owija pułapki):
  start    → systemctl --user start live-recording.target
  restart  → systemctl --user stop live-recording.target && … start   (PartOf pociąga członków)
  stop     → systemctl --user stop live-recording.target
  status   → systemctl --user status + GET /health
```

## Implementation Units

- [x] **Unit 1: Szkielet repo `deploy/live/` + instalator**

**Goal:** Miejsce na wersjonowane unity i skrypty + jedna komenda instalująca je do
katalogów użytkownika.

**Requirements:** R6

**Dependencies:** brak

**Files:**
- Create: `deploy/live/README.md` (instrukcja instalacji, mapa plików, pułapki operatorskie)
- Create: `deploy/live/install.sh` (kopiuje unity→`~/.config/systemd/user/`, skrypty→
  `~/.local/bin/`, `systemctl --user daemon-reload`, wyłącza stary kiosk-autostart)
- Test: `deploy/live/tests/test_install.sh` (plain shell — `bats` nie jest w środowisku)

**Approach:**
- Naśladuj styl `packages/paternologia/deploy/` (ABOUTME w nagłówku, `%h`, komentarze).
- `install.sh` idempotentny: ponowne uruchomienie nie psuje stanu; backup istniejących
  plików przed nadpisaniem; jawny komunikat co zostało zainstalowane.
- Wyłączenie starego autostartu: `mv ~/.config/autostart/paternologia-kiosk.desktop`
  do backupu (nie kasować — odwracalność), bo kiosk przechodzi pod systemd (Unit 5).

**Patterns to follow:** `packages/paternologia/deploy/paternologia.service`,
`packages/obsession/scripts/deploy_cameras.sh`.

**Test scenarios:**
- Happy path: `install.sh` na czystym `~/.config/systemd/user/` kopiuje wszystkie unity i
  uruchamia `daemon-reload` (zweryfikuj exit 0 i obecność plików).
- Edge case: ponowne uruchomienie gdy pliki już istnieją → robi backup, nie duplikuje,
  exit 0 (idempotencja).
- Edge case: brak `paternologia-kiosk.desktop` w autostarcie → krok wyłączenia to no-op,
  nie błąd.
- Error path: brak `~/.local/bin` w PATH → instalator ostrzega, ale kończy się sukcesem.

**Verification:** Po `install.sh` `systemctl --user list-unit-files | grep live` pokazuje
nowe unity; stary kiosk-autostart nieobecny w `~/.config/autostart/`.

---

- [x] **Unit 2: `live-preflight.service` (oneshot gate) + skrypt warunków**

**Goal:** Twarda, jednomiejscowa weryfikacja gotowości audio/MIDI/paternologii zanim
wstanie warstwa GUI.

**Requirements:** R2

**Dependencies:** Unit 1 (miejsce w repo)

**Files:**
- Create: `deploy/live/units/live-preflight.service`
- Create: `deploy/live/bin/live-preflight.sh` (logika sprawdzeń + czytelne komunikaty)
- Test: `deploy/live/tests/test_live_preflight.sh` (plain shell — `bats` nie jest w środowisku)

**Approach:**
- Unit: `Type=oneshot`, `RemainAfterExit=yes`, `After=paternologia.service`,
  `PartOf=live-recording.target` (by `stop` targetu i `setka-live restart` re-weryfikowały
  warunki — patrz Unit 6), `TimeoutStartSec` z zapasem na polling `/health`.
- Skrypt sprawdza po kolei, każdy warunek z osobnym komunikatem i niezerowym exit przy
  niespełnieniu:
  1. `hw:Virmidi` obecny (np. `aplaymidi -l`/`lsmod | grep snd_virmidi`) — komunikat
     „załaduj snd-virmidi" jeśli brak.
  2. PipeWire `clock.rate == 44100` (`pw-metadata -n settings`) — **wydobyć dokładnie klucz
     `clock.rate`**, nie ogólny grep „rate": `pw-metadata -n settings` zwraca też
     `clock.allowed-rates` (`[44100 48000]`) i `clock.force-rate` (`0`), które zawierają
     podciąg „rate" i wartości liczbowe → naiwny grep da fałszywy wynik. Komunikat o złym rate.
  3. `GET http://127.0.0.1:8000/health` → `pacer_input_open` i `bridge_port_active` true
     (polling z krótkim retry, jak istniejący kiosk poll). **127.0.0.1, nie `localhost`** —
     uvicorn binduje `127.0.0.1`, a `localhost` może rozwiązać się na `::1` (IPv6) i chybić.
- **Retry/grace, nie pojedynczy strzał** (twardy blok `Requires=` jest właściwy, ale nie
  może wywracać startu na chwilowym stanie): każdy warunek pollowany z krótkim retry/grace,
  dostrojonym pod watchdog paternologii (`RestartSec=2`, `WatchdogSec=10`) i stabilizację
  PipeWire po wybudzeniu — np. ~5–10 s łącznego okna na warunek. Dopiero wyczerpanie retry =
  twardy fail. To redukuje fałszywie-negatywne blokady (PACER chwilowo odpięty, graf audio
  jeszcze się ustala) bez rezygnacji z fail-fast.
- Preflight sprawdza **tylko** `pacer_input_open && bridge_port_active`, **nie** `obs_connected`
  — OBS startuje *po* preflighcie, więc websocket nie jest jeszcze podniesiony; pełne zdrowie
  (z `obs_connected`) raportuje `setka-live status`.
- Preflight **tylko weryfikuje** — nie ładuje virmidi ani nie restartuje PipeWire
  (restart PipeWire jest zabroniony pod żywym Bitwigiem; tu Bitwig jeszcze nie żyje, ale
  trzymamy zasadę „preflight nie modyfikuje audio"). Sprawdzenie virmidi jest **defensywne**:
  moduł jest utrwalony na boot (Scope Boundaries), ale rzadki przypadek braku (np. ręczny
  `rmmod`) ma dać czytelny fail, nie cichy rozjazd MIDI.

**Execution note:** Logikę warunków pisz test-first — to jedyny realnie testowalny
fragment z rozgałęzieniami; unity systemd są deklaratywne.

**Patterns to follow:** polling z `~/.local/bin/paternologia-kiosk.sh` (pętla `until` +
`curl -sf`).

**Test scenarios:**
- Happy path: wszystkie trzy warunki spełnione → exit 0, log „preflight OK".
- Error path: brak `snd-virmidi` → exit ≠ 0, komunikat wskazuje moduł do załadowania.
- Error path: PipeWire na 48000 → exit ≠ 0, komunikat o rate (cytuj wymóg 44100).
- Error path: `/health` zwraca `pacer_input_open=false` → exit ≠ 0, komunikat „podłącz
  PACER".
- Edge case: paternologia nie odpowiada (timeout HTTP) → exit ≠ 0 po wyczerpaniu retry,
  nie zawiesza się w nieskończoność.
- Integration: `systemd-analyze --user verify live-preflight.service` bez ostrzeżeń.

**Verification:** `systemctl --user start live-preflight.service` zielony tylko gdy
realnie gotowe; `systemctl --user status` pokazuje `active (exited)` i log warunków.

---

- [x] **Unit 3: `obs.service`**

**Goal:** OBS Studio jako nadzorowany przez systemd, bez auto-restartu, gated preflightem.

**Requirements:** R1, R2, R4

**Dependencies:** Unit 2 (preflight)

**Files:**
- Create: `deploy/live/units/obs.service`

**Approach:**
- `Type=exec`, `ExecStart=/usr/bin/obs` (rozważ `--startrecording`? — **nie**, start
  nagrania idzie przez PACER/websocket; OBS ma tylko wstać gotowy).
- `Restart=no` (jawnie, z komentarzem dlaczego — ochrona pliku nagrania).
- `Requires=live-preflight.service`, `After=live-preflight.service graphical-session.target`.
- `PartOf=live-recording.target`, `WantedBy=live-recording.target`.
- `ConditionEnvironment=DISPLAY`.
- `KillMode=control-group`, `TimeoutStopSec=30s` (zapas na flush pliku; SIGTERM → OBS
  domyka).

**Patterns to follow:** `packages/paternologia/deploy/paternologia.service` (styl, ABOUTME).

**Test scenarios:**
- Integration: `systemd-analyze --user verify obs.service` bez ostrzeżeń.
- Integration: start gdy preflight nie przeszedł → OBS **nie** startuje (`Requires`
  blokuje), status pokazuje zależność jako przyczynę.
- Manual/E2E: `systemctl --user start obs.service` po zielonym preflighcie → OBS okno;
  `stop` → OBS znika czysto w granicy `TimeoutStopSec` (brak osieroconych procesów
  w cgroup).

**Verification:** OBS startuje tylko po preflighcie; zatrzymanie nie zostawia procesów
(`systemctl --user status obs.service` → `inactive (dead)`).

---

- [x] **Unit 4: `bitwig.service` (flatpak)**

**Goal:** Bitwig (flatpak) jako nadzorowany przez systemd, czysto zatrzymywalny, bez
auto-restartu.

**Requirements:** R1, R2, R4

**Dependencies:** Unit 2 (preflight gwarantuje PipeWire 44100 + virmidi przed startem)

**Files:**
- Create: `deploy/live/units/bitwig.service`

**Approach:**
- `Type=exec`, `ExecStart=/usr/bin/flatpak run com.bitwig.BitwigStudio` (main PID = bwrap).
- `ExecStop=/usr/bin/flatpak kill com.bitwig.BitwigStudio` (czyste domknięcie sandboxa).
- `Restart=no`, `KillMode=control-group`, `TimeoutStopSec=60s` (zapas na zapis sesji).
- `Requires=live-preflight.service`, `After=live-preflight.service graphical-session.target`,
  `PartOf=live-recording.target`, `WantedBy=live-recording.target`,
  `ConditionEnvironment=DISPLAY`.
- Komentarz w unicie: po starcie wymagana ręczna weryfikacja Audio Engine + MIDI Input =
  „Virtual Raw MIDI 1" (nieautomatyzowalne — `docs/solutions`).

**Patterns to follow:** ten sam szablon co `obs.service`; różnice flatpakowe z research.

**Test scenarios:**
- Integration: `systemd-analyze --user verify bitwig.service` bez ostrzeżeń.
- Integration: start bez preflightu → blokada przez `Requires`.
- Manual/E2E: start → okno Bitwiga; `stop` → `flatpak kill` domyka, brak osieroconego
  `bwrap` w `flatpak ps` po `TimeoutStopSec`.
- Manual/E2E: po starcie Bitwig widzi „Virtual Raw MIDI 1" i trigger Note z PACER dociera
  mostem (potwierdza, że kolejność virmidi→bitwig zadziałała).

**Verification:** Bitwig startuje po preflighcie; `stop` nie zostawia procesów flatpaka
(`flatpak ps` pusty dla Bitwiga).

---

- [x] **Unit 5: `kiosk.service` (migracja kiosku pod systemd)**

**Goal:** Okno `/live` paternologii w `brave --kiosk` jako członek targetu (zamiast
XDG autostartu przy logowaniu).

**Requirements:** R1, R5

**Dependencies:** Unit 2 (preflight już potwierdza, że paternologia HTTP odpowiada)

**Files:**
- Create: `deploy/live/units/kiosk.service`
- Create: `deploy/live/bin/paternologia-kiosk.sh` (wersjonowana kopia istniejącego skryptu)
- Modify (w ramach Unit 1 install): wycofanie `~/.config/autostart/paternologia-kiosk.desktop`

**Approach:**
- Przenieś istniejący `~/.local/bin/paternologia-kiosk.sh` do repo bez zmiany logiki
  (osobny `--user-data-dir`, `--kiosk`, poll serwera). Poll można skrócić, bo preflight
  już gwarantuje żywą paternologię — ale **zostawiamy** poll dla odporności (KISS:
  najmniejsza zmiana, nie przepisujemy działającego skryptu).
- Unit: `Type=exec`, `ExecStart=…/paternologia-kiosk.sh`, `Restart=no`,
  `Requires=live-preflight.service`, `After=live-preflight.service graphical-session.target`,
  `PartOf=live-recording.target`, `WantedBy=live-recording.target`,
  `ConditionEnvironment=DISPLAY`, `KillMode=control-group`.

**Patterns to follow:** istniejący `~/.local/bin/paternologia-kiosk.sh` (zachować 1:1).

**Test scenarios:**
- Integration: `systemd-analyze --user verify kiosk.service` bez ostrzeżeń.
- Happy path (skrypt): serwer odpowiada → `brave --kiosk` na `/live` z osobnym profilem.
- Edge case (skrypt): serwer milczy → poll do timeoutu, potem czysty błąd (nie wisi).
- Manual/E2E: `stop` zamyka okno kiosku i wszystkie renderery Brave (cgroup czysty).

**Verification:** Po starcie targetu okno `/live` jest na wierzchu; po `stop` znika bez
osieroconych procesów Brave; logowanie do GNOME **nie** odpala już kiosku samo z siebie.

---

- [x] **Unit 6: `live-recording.target` + skrypt operatorski `setka-live`**

**Goal:** Jeden target spinający członków (tryb na żądanie) i jedna komenda do
start/stop/restart, omijająca pułapkę restartu targetu (R3).

**Requirements:** R1, R3, R5

**Dependencies:** Unit 2–5 (członkowie muszą istnieć)

**Files:**
- Create: `deploy/live/units/live-recording.target`
- Create: `deploy/live/bin/setka-live` (start|stop|restart|status)
- Test: `deploy/live/tests/test_setka_live.sh` (plain shell — `bats` nie jest w środowisku)

**Approach:**
- Target: `Wants=obs.service bitwig.service kiosk.service`, **bez**
  `WantedBy=default.target` (na żądanie). Sam target bez logiki.
- `setka-live restart`: `systemctl --user stop live-recording.target && systemctl --user
  start live-recording.target` — działa dzięki `PartOf=` na członkach; **nie** używa
  `restart <target>` (pułapka). Komentarz w skrypcie cytuje powód.
- **Re-weryfikacja preflight przy restarcie:** `live-preflight.service` jest `oneshot` +
  `RemainAfterExit=yes`, więc po pierwszym starcie zostaje `active (exited)`. Żeby restart
  realnie ponownie sprawdził audio/MIDI (operator restartuje *bo coś się rozjechało*),
  preflight ma `PartOf=live-recording.target` (Unit 2) — `stop` targetu go gasi, a `start`
  odpala od nowa. Dla pewności `setka-live restart` jawnie dorzuca `live-preflight.service`
  do ścieżki stop, by nie polegać wyłącznie na propagacji.
- `setka-live status`: `systemctl --user status` członków + `GET /health` (jeden widok
  zdrowia: czy bridge/PACER/OBS-websocket żyją).
- **paternologia poza zakresem `setka-live`**: skrypt nigdy nie restartuje mostu MIDI (by
  nie zrywać fan-outu PACER). Rzadki restart mostu robi się jawnie i ręcznie:
  `systemctl --user restart paternologia.service`. (Flagi `--with-bridge` świadomie nie
  dodajemy — YAGNI; doda się dopiero gdy pojawi się realna częstość użycia.)
- **Świadomie nie** restartujemy PipeWire w żadnej ścieżce (zakaz pod żywym Bitwigiem) —
  jeśli audio się rozjedzie, to ręczny „Restart Audio Engine" w Bitwigu (log podpowiada).

**Patterns to follow:** styl skryptów w `packages/*/scripts/` (set -euo pipefail, ABOUTME).

**Test scenarios:**
- Integration: `systemd-analyze --user verify live-recording.target` bez ostrzeżeń.
- Happy path: `setka-live start` → wszyscy trzej członkowie `active` (po preflighcie).
- Happy path (R3): `setka-live restart` → członkowie przeszli przez stop→start (np.
  porównanie `ActiveEnterTimestamp` przed/po, albo świeże PID-y), target wstał ponownie.
- Edge case: `setka-live restart` gdy nic nie działało → po prostu startuje (stop to no-op).
- Integration (R3 + preflight): po `setka-live restart` `live-preflight.service` przeszedł
  ponowny cykl (świeży `ActiveEnterTimestamp`) — czyli audio/MIDI były re-weryfikowane, a nie
  pominięte przez wiszący `active (exited)`.
- Edge case: `setka-live status` gdy paternologia padła → raportuje czerwone `/health`,
  nie wywala się.
- Integration: po `setka-live restart` PID `paternologia.service` **się nie zmienia** —
  most MIDI nietknięty (skrypt nigdy go nie tyka).
- Manual/E2E: pełny przebieg — `setka-live start` z zimnego stanu stawia komplet gotowy do
  nagrania w poprawnej kolejności.

**Verification:** `setka-live start` z jednej komendy stawia komplet; `setka-live restart`
realnie restartuje całą warstwę GUI (członkowie mają nowe PID-y), a `paternologia.service`
zostaje nietknięta.

## System-Wide Impact

- **Interaction graph:** target dotyka OBS, Bitwiga, Brave i (przez ordering) paternologii.
  Nowe unity wpinają się do user systemd; stary XDG autostart kiosku jest wycofywany —
  jedyna zmiana zachowania przy logowaniu (kiosk już nie wstaje sam).
- **Error propagation:** preflight `Requires=` twardo blokuje GUI gdy audio/MIDI nie gotowe
  (świadome, czytelne fail-fast). Crash OBS/Bitwiga **nie** propaguje na resztę (`Wants`,
  nie `Requires`, między członkami) i **nie** jest wznawiany (`Restart=no`).
- **State lifecycle risks:** za krótki `TimeoutStopSec` = SIGKILL = uszkodzony plik
  nagrania OBS / utracona sesja Bitwiga — stąd zapas i `KillMode=control-group`. Brave
  kiosk ma osobny `--user-data-dir`, więc stop nie rusza zwykłej przeglądarki.
- **API surface parity:** komendy operatora skupione w `setka-live` (start/stop/restart/
  status) — jedno źródło prawdy zamiast luźnych `systemctl`; dokumentacja w `deploy/live/README.md`.
- **Integration coverage:** `systemd-analyze verify` na wszystkich unitach + manualny
  E2E pełnego przebiegu (zimny start → nagranie) to jedyny dowód, że kolejność i
  środowisko graficzne realnie działają na tej maszynie — testy jednostkowe tego nie
  udowodnią.

## Risks & Dependencies

- **Pułapka restartu targetu** (R3): zaadresowana `PartOf=` + `stop && start` w skrypcie.
  Ryzyko regresji jeśli ktoś „uprości" skrypt do `restart <target>` — komentarz w kodzie
  ostrzega.
- **`After=graphical-session.target` jest tylko kosmetyczne w trybie na żądanie**: operator
  jest już zalogowany, więc target jest aktywny, a `After=` to wyłącznie ordering wobec
  czegoś-już-aktywnego (no-op). Realnym bezpiecznikiem gotowości środowiska graficznego jest
  `ConditionEnvironment=DISPLAY`, nie ten ordering — nie traktować go jako gwarancji.
- **Środowisko graficzne**: na X11 `DISPLAY=:1` jest już w activation environment (zweryfikowane),
  więc `ConditionEnvironment=DISPLAY` jest spełniony i GUI usługi dziedziczą DISPLAY.
  Ryzyko zostaje, **jeśli maszyna kiedyś przejdzie na Wayland** — wtedy `DISPLAY` zniknie i
  trzeba przełączyć warunek na `WAYLAND_DISPLAY` (+ ewentualny `dbus-update-activation-environment`).
  `setka-live status` ma raportować obecność `DISPLAY`/`WAYLAND_DISPLAY` w activation env jako
  diagnostykę.
- **Audio jest poza orkiestracją**: PipeWire 44100 i `snd-virmidi` muszą być utrwalone
  (są). Preflight to wyłapie, ale nie naprawi. **Nigdy** nie restartować PipeWire pod
  żywym Bitwigiem — skrypt celowo tego nie robi.
- **Logi flatpaka w journalu** bywają nieskojarzone z `bitwig.service` — utrudnia debug;
  odnotowane w `deploy/live/README.md`.
- **Zależność zewnętrzna**: OBS musi mieć włączony WebSocket Server (jest); Bitwig
  skonfigurowany kontroler (jednorazowo, poza tym planem).

## Documentation / Operational Notes

- `deploy/live/README.md`: instalacja, mapa unitów, komendy `setka-live`, lista pułapek
  (restart targetu, audio engine, logi flatpaka), procedura recovery zawieszonego Bitwiga
  (`pkill -9 -f BitwigAudioEngine` + ręczny Restart Audio Engine).
- Zaktualizować główny `CLAUDE.md` (sekcja „Practical Usage Examples") o jeden wpis:
  `setka-live start` jako krok 0 pipeline'u live.

## Sources & References

- Wzorzec usługi: `packages/paternologia/deploy/paternologia.service`
- Skrypt kiosk: `~/.local/bin/paternologia-kiosk.sh`
- Learnings: `docs/solutions/2026-06-01-bitwig-pipewire-44100-usb-audio-contention.md`,
  `docs/solutions/2026-06-02-bitwig-alsa-seq-invisible-virmidi-bridge.md`
- Kontekst MIDI: `docs/plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md`
- systemd restart-targetu: issues #13841, #24068, #32382
- flatpak pod systemd: flatpak issues #5870, #3340; `systemd.kill(5)`
- GNOME Wayland env: sway Systemd integration wiki, Arch Wiki UWSM
