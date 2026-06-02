---
date: 2026-05-31
topic: midi-recording-orchestration
---

# Orkiestracja nagrywania: OBS + Bitwig + paternologia

## Problem Frame

Wojtas gra live na sprzętowym rigu MIDI (PACER footswitch = master CC source, RC-600 =
master MIDI clock + Start/Stop, M:S, MicroFreak, LCXL3). Performance nagrywa w OBS (canvas
recording → MKV + metadata) i chce dorzucić wielościeżkowy capture w Bitwigu. Dziś bolą trzy
rzeczy:

1. **Dwa ruchy zamiast jednego** — start nagrywania w OBS i w Bitwigu to dwie osobne, ręczne
   akcje.
2. **Konflikt o PACER na Linuksie** — paternologia (live song state z nasłuchu PACER przez
   `rtmidi`/ALSA seq) i Bitwig (PACER jako kontroler, dostęp raw) walczą o ten sam port →
   `Device or resource busy`. Dochodził drugi bloker: przypadkowa zakładka Chrome z Web MIDI
   trzymająca LCXL3 (niezwiązana z UI paternologii).
3. **Brak maszynowego zapisu, jaki utwór/pattern był aktywny i kiedy**, zsynchronizowanego z
   nagraniem — co blokuje automatyzację post-prod (Beatrix/Cinemon).

Cel: jeden fundament, który rozwiązuje konflikt MIDI, daje start jednym ruchem, utrzymuje
podgląd stanu utworu i produkuje timeline utworów jako dane.

## Requirements

- **R1.** paternologia jest **jedynym właścicielem/czytelnikiem fizycznego wejścia PACER** i
  re-broadcastuje potrzebne komunikaty (CC/PC) do Bitwiga przez **stabilny wirtualny port
  MIDI**. Bitwig nie otwiera już sprzętowego PACER bezpośrednio. (Model A — deterministyczne
  rozwiązanie konfliktu raw vs seq.)
- **R2.** **Dedykowany przycisk PACER** startuje nagrywanie jednocześnie w **OBS** (przez
  obs-websocket `StartRecord`) i w **Bitwigu** (transport record). **Drugi dedykowany przycisk
  PACER** zatrzymuje oba. Bitwig: minimum to wystartowanie transport record; jeśli wykonalne
  — uzbrojenie wszystkich ścieżek (lub upewnienie się, że są uzbrojone) jako nice-to-have.
- **R3.** paternologia wyprowadza **bieżący utwór/pattern** z PACER (Program Change → utwór) i
  udostępnia go live przez **istniejące web UI (SSE, `/live/events`)** — bez zmiany ducha.
  Front **nie używa Web MIDI** (zweryfikowane: korzysta z `EventSource`).
- **R4.** Gdy nagranie trwa, paternologia zapisuje **timeline zmian utworu/patternu znakowany
  czasem względem startu nagrania**, trwale w strukturze nagrania, tak by post-prod
  (Beatrix/Cinemon) mógł konsumować granice sekcji utworów.
- **R5.** paternologia zostaje **przeniesiona do setka-monorepo jako pakiet uv workspace**,
  reużywając `RecordingStructureManager`, żeby timeline lądował w strukturze nagrania.
- **R6.** System ma być **niezawodny w live**: ścieżka fan-outu MIDI i trigger nagrywania mają
  przetrwać cały występ; paternologia auto-startuje i sygnalizuje swój stan zdrowia.

## Success Criteria

- Bitwig i paternologia działają jednocześnie z PACER — **zero `Device or resource busy`**.
- Jedno naciśnięcie przycisku PACER → start pliku OBS i nagrania Bitwiga w wąskim oknie czasu;
  drugi przycisk → stop obu.
- Po sesji katalog nagrania zawiera **timeline utworów/patternów zsynchronizowany ze startem
  nagrania**.
- Web UI paternologii pokazuje poprawny live stan utworu przez cały występ, ze źródłem w
  backendzie (bez Web MIDI).

## Scope Boundaries

- **Bez** integracji stanu utworu w fermacie (odłożone; web UI zostaje).
- **Bez** overlay/browser-source w OBS (możliwy późniejszy bonus).
- **Bez** zmian w routingu clock/transport RC-600 ani w „plumbing" Doremidi Split/Merge.
- **Bez** generowania projektów Bitwiga / DAWproject.
- **Bez** OSC/DrivenByMoss — Model A używa wirtualnego MIDI, nie OSC (chyba że planowanie
  wykaże, że record w Bitwigu inaczej się nie da wyzwolić).

## Key Decisions

- **Model A (paternologia = jedyny właściciel PACER + fan-out)** zamiast Bitwig-master czy
  współdzielenia seq: jedyny deterministyczny fix konfliktu, spójny z uczynieniem paternologii
  centralnym hubem, odblokowuje timeline „za darmo".
- **Trigger = dedykowany footswitch PACER** (wolne ręce w live); stop = drugi dedykowany
  przycisk.
- **Surface stanu = istniejące web UI paternologii** (SSE; zweryfikowane, że nie używa Web
  MIDI).
- **Miejsce kodu = pakiet w setka-monorepo** (synergia z `RecordingStructureManager` +
  przyszła integracja z fermatą).

## Dependencies / Assumptions

- OBS 28+ z wbudowanym obs-websocket (domyślnie port 4455) — włączony.
- PACER emituje tylko CC/PC; MIDI clock/transport idzie z RC-600 osobno → zakres fan-outu jest
  mały (bez forwardowania clocka).
- Stray „Chrome (output)" Web MIDI trzymający LCXL3 jest niezwiązany z paternologią i zamykany
  przez użytkownika.
- „Bitwig nagrywa" = transport record; multitrack USB capture (8 ścieżek z RC-600 USB,
  dual-mode studio) jest celem, ale arming wszystkich ścieżek to nice-to-have zależne od
  wykonalności.

## Outstanding Questions

### Deferred to Planning

- [Affects R1][Needs research] Mechanizm wirtualnego portu MIDI dla fan-outu do Bitwiga
  (`rtmidi` virtual port vs ALSA `snd-virmidi`) + jak Bitwig stabilnie subskrybuje go pod
  Flatpakiem.
- [Affects R2][Needs research] Jak wyzwolić transport record w Bitwigu z MIDI (mapping CC/note
  → record) i czy/jak uzbroić wszystkie ścieżki programowo (MIDI mapping vs Controller
  Extension API).
- [Affects R2][Technical] Konfiguracja obs-websocket (port, hasło, autostart serwera) i klient
  WS w paternologii (`StartRecord`/`StopRecord`).
- [Affects R4][Technical] Format i lokalizacja timeline (np. `analysis/song_timeline.json` w
  strukturze nagrania) + skąd brać czas startu nagrania OBS (event z websocket vs
  `obs_script.py`).
- [Affects R5][Technical] Mechanika migracji do uv workspace (członek workspace, zależności
  `rtmidi`/`fastapi`, testy, entry points, ścieżki danych `data/`/`workspace/`).
- [Affects R6][Technical] Auto-start/supervision paternologii (systemd user service) +
  wskaźnik zdrowia w UI; zachowanie fan-outu, gdy paternologia padnie w trakcie występu.

## Next Steps

→ `/ce:plan` — wszystkie blokujące decyzje produktowe rozstrzygnięte; pozostałe pytania są
techniczne i należą do planowania.
