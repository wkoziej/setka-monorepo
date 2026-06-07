---
title: "feat: Start/stop warstwy live w menu traya setka-tray"
type: feat
status: completed
date: 2026-06-07
origin: docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md
---

# feat: Start/stop warstwy live w menu traya setka-tray

## Overview

Menu ikony tray (`setka-tray`) eksponuje dziś tylko akcje wewnątrz-sesyjne
(`show`, `new-take`, `delete-last`) oraz `Zakończ`. `setka-live` ma już komplet
komend cyklu życia (`start`/`stop`/`restart`/`status`), ale operator nie może
postawić ani zatrzymać całej warstwy live z poziomu traya — musi zejść do
terminala. Ta zmiana dodaje do menu **Uruchom** i **Zatrzymaj**, a ponieważ
`stop` ubija `live-recording.target` (w tym `obs.service` — przerwałoby trwające
nagranie), `setka-live stop` zyskuje bramkę potwierdzenia.

## Problem Frame

Wyzwalacz „postaw / zatrzymaj warstwę live" musi być dostępny globalnie, bez
terminala — tak samo jak pozostałe akcje operatorskie z traya (patrz origin:
`docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md`, R1).
Origin-doc wprost odłożył to pytanie do planowania:

> [Affects R2] Czy launcher ma eksponować więcej komend niż `show` i usuwanie
> (np. `restart`, `status`)? Domyślnie startujemy z dwiema akcjami, struktura
> rozszerzalna.

Decyzja operatora w tej iteracji: **tylko `start` + `stop`** (bez `restart`/`status`).

## Requirements Trace

- **R1.** Globalny wyzwalacz dostępny niezależnie od aktywnego okna — tu: pozycje
  menu w trayu odpalające `setka-live start` / `setka-live stop`. (origin R1)
- **R-new-1.** Menu traya zawiera pozycję uruchamiającą `["setka-live", "start"]`.
- **R-new-2.** Menu traya zawiera pozycję uruchamiającą `["setka-live", "stop"]`.
- **R-new-3.** `setka-live stop` przeniesiony do trybu „potwierdź przed akcją":
  bez jawnego potwierdzenia (zenity) nie zatrzymuje targetu — chroni przed
  przypadkowym ubiciem trwającego nagrania OBS. (analogiczne do origin R4 dla
  delete-last)
- **R-new-4.** `setka-live restart` pozostaje bez potwierdzenia (świadoma akcja
  ratunkowa; woła `sctl stop` bezpośrednio, nie przez `cmd_stop`).

## Scope Boundaries

- **Bez `restart` i `status` w trayu** — świadomie odłożone (decyzja operatora).
  `restart`/`status` zostają dostępne w terminalu. `status` i tak wymagałby innego
  potraktowania niż fire-and-forget Popen (wynik leci na stdout — w trayu byłby
  niewidoczny).
- **Bez globalnych skrótów klawiszowych dla start/stop** — ta iteracja dotyczy
  wyłącznie menu traya. (Skróty dla show/delete/new-take istnieją; start/stop
  można dodać osobno, jeśli zajdzie potrzeba — patrz Deferred.)
- **Bez zmiany mechaniki `start`** — pozostaje fire-and-forget (jak `show`);
  rezultat (okna) widać na ekranie, layout jest best-effort po starcie.
- **Bez twardego guardu „OBS nagrywa"** — bezpieczeństwo `stop` przez
  potwierdzenie + odwracalność (`start` stawia warstwę z powrotem), spójnie z
  filozofią origin R6.

## Context & Research

### Relevant Code and Patterns

- `deploy/live/bin/setka-tray` — czysta tabela `build_menu_items()` zwraca listę
  krotek `(etykieta, argv|None)`; `(None, None)` = separator; `argv=None` = wyjście
  (`Zakończ`). Warstwa GTK tylko w `main()`. **Wzorzec do naśladowania 1:1.**
- `deploy/live/bin/setka-live`:
  - `cmd_stop()` (linie ~73-75) — dziś `sctl stop "$TARGET"`. Tu dochodzi bramka.
  - `cmd_delete_last()` (linie ~284-351) — **wzorzec bramki zenity**: `command -v`
    na `$ZENITY_BIN`, `--question --default-cancel --icon=... --title=... --text=...`,
    `rc != 0 → log "Anulowano" + return 0` (fail-safe), `NOTIFY_BIN` best-effort.
  - `cmd_restart()` (linie ~77-85) — woła `sctl stop "$TARGET" live-preflight.service`
    **bezpośrednio**, NIE przez `cmd_stop` → automatycznie omija nową bramkę. Nie zmieniać.
  - `usage()` (linie ~35-58) — opis podkomend + sekcje env do uzupełnienia.
  - `ZENITY_BIN`/`NOTIFY_BIN` (linie ~12-14) — już zadeklarowane, gotowe do użycia.
- `deploy/live/tests/test_setka_tray.py` — testy czystej tabeli przez
  `SourceFileLoader` (bez GTK). Wzorzec: `labels = {label: argv ...}`, asercja na
  mapowanie etykieta→argv. **Wzorzec do naśladowania dla nowych pozycji.**
- `deploy/live/tests/test_setka_live.sh` — harness z rejestratorami-stubami:
  `SYSTEMCTL_BIN` (`$REC` + `$REC_LOG`), `ZENITY_BIN` (`$ZENITY_REC`, override
  `ZENITY_RC`), `NOTIFY_BIN`. Istniejący test `stop` (linie ~50-54) woła
  `run_setka stop` i asercję `--user stop live-recording.target`. **Ten test
  trzeba zaktualizować** — po dodaniu bramki `stop` wymaga wstrzyknięcia zenity-stuba.

### Institutional Learnings

- `[[gnome-keybinding-clean-env]]` — komendy ze skrótów/systemd startują w czystym
  env (bez IFS/SHELLOPTS). Nie dotyczy bezpośrednio traya (uruchamiany z sesji
  GNOME), ale potwierdza, że `setka-live` musi działać bez założeń o env powłoki.
- `[[cinemon-fermata-preset-drift]]` — ostrzeżenie ogólne: przyciski hardkodujące
  nieistniejące komendy to realny dryf. Tu ryzyko zażegnane — `start`/`stop` już
  istnieją w `setka-live` (zweryfikowane w `main()` i `usage()`).

### External References

- Nie potrzebne. Wzorce lokalne są mocne (tabela menu, bramka zenity, harness
  testów bash) — ≥3 bezpośrednie przykłady w tym samym katalogu. Bez researchu zewn.

## Key Technical Decisions

- **Tylko `start` + `stop` w trayu** (decyzja operatora): minimalny, czytelny
  zestaw; struktura tabeli pozostaje rozszerzalna o `restart` później.
- **Potwierdzenie dla `stop` żyje w `cmd_stop` (setka-live), nie w trayu** (DRY,
  single source of truth): tray to cienki wyzwalacz; każdy konsument `setka-live
  stop` (tray, terminal, ewentualny przyszły skrót) dostaje tę samą ochronę.
  Spójne z wzorcem origin (bramka delete-last żyje w `setka-live`, nie w trayu).
- **`--yes`/`-y` jako jawna furtka omijająca potwierdzenie** (mitygacja regresji):
  hard-gate `stop` wyłącznie na zenity zablokowałby zatrzymanie warstwy, gdy
  display jest zepsuty (a to właśnie wtedy chcesz móc ją ubić, np. po SSH).
  `setka-live stop --yes` pomija dialog. **Tray NIE przekazuje `--yes`** → klik w
  trayu zawsze pyta. Bez zenity i bez `--yes` → odmowa z komunikatem wskazującym
  `--yes` (zawsze istnieje droga ucieczki).
- **`restart` pozostaje bez potwierdzenia**: `cmd_restart` woła `sctl stop`
  bezpośrednio, więc nowa bramka go nie dotyczy — i nie powinna (restart to
  świadoma akcja ratunkowa, nie przypadkowy klik).
- **Placement: cykl życia na górze menu, oddzielony separatorem od akcji
  wewnątrz-sesyjnych**: „Uruchom" / „Zatrzymaj" → separator → „Pokaż okna" /
  „Nowy projekt Bitwig" / „Usuń ostatnie nagranie" → separator → „Zakończ".
  Grupuje semantykę (postaw/zburz warstwę vs operacje w trakcie sesji).
- **Etykiety: „Uruchom warstwę live" / „Zatrzymaj warstwę live"** — spójne z
  terminologią README („warstwa live"/„warstwa GUI") i stylem istniejących
  etykiet (imperatyw, opis akcji). Do drobnej korekty na życzenie.

## Open Questions

### Resolved During Planning

- **Czy eksponować restart/status?** → Nie, tylko start+stop (decyzja operatora).
- **Czy stop potwierdzać?** → Tak, zenity w `cmd_stop`, z furtką `--yes` (decyzja
  operatora + mitygacja regresji headless).
- **Czy potwierdzenie zepsuje restart?** → Nie: `cmd_restart` woła `sctl stop`
  bezpośrednio, omijając `cmd_stop`.

### Deferred to Implementation

- **Dokładne brzmienie tekstu dialogu zenity dla `stop`** — sformułowanie
  ostrzeżenia (że ubije OBS/Bitwig/kiosk i przerwie ewentualne nagranie) ustali
  się przy pisaniu; wzór: `cmd_delete_last` `msg`.
- **Czy istniejący test `stop` (test_setka_live.sh:50-54) tylko rozszerzyć o
  zenity-stub, czy dopisać osobne przypadki** — rozstrzygnie się przy edycji
  harnessu (zachować zielony invariant „woła stop target", dołożyć cancel/--yes).

## Implementation Units

- [x] **Unit 1: Pozycje start/stop w tabeli menu setka-tray**

**Goal:** Menu traya zawiera „Uruchom warstwę live" → `["setka-live","start"]`
i „Zatrzymaj warstwę live" → `["setka-live","stop"]`, zgrupowane separatorem.

**Requirements:** R1, R-new-1, R-new-2

**Dependencies:** Brak (czysta tabela; `setka-live start`/`stop` już istnieją).

**Files:**
- Modify: `deploy/live/bin/setka-tray` (funkcja `build_menu_items()`)
- Test: `deploy/live/tests/test_setka_tray.py`

**Approach:**
- Dołożyć na **początku** listy dwie krotki: `("Uruchom warstwę live",
  ["setka-live","start"])`, `("Zatrzymaj warstwę live", ["setka-live","stop"])`,
  potem `(None, None)` separator, dalej istniejące pozycje bez zmian.
- Warstwa GTK w `main()` nie wymaga zmian — pętla już obsługuje krotki/separatory.
- `run_command` (fire-and-forget Popen) bez zmian — pasuje do start/stop.

**Patterns to follow:**
- Istniejące krotki w `build_menu_items()` (np. „Pokaż okna").

**Test scenarios:**
- Happy path: `build_menu_items()` zawiera „Uruchom warstwę live" mapujące na
  `["setka-live","start"]`.
- Happy path: zawiera „Zatrzymaj warstwę live" mapujące na `["setka-live","stop"]`.
- Edge case: menu nadal zawiera wszystkie poprzednie pozycje (show/new-take/
  delete-last/Zakończ) — brak regresji (asercje istniejące pozostają zielone).
- Edge case: „Zakończ" wciąż ma `argv=None`; tabela wciąż zwraca listę 2-krotek
  (istniejące `test_menu_zwraca_liste_krotek` / `test_zakoncz_*` bez zmian).

**Verification:**
- `pytest deploy/live/tests/test_setka_tray.py` zielony; nowe pozycje obecne,
  stare nienaruszone.

- [x] **Unit 2: Bramka potwierdzenia w setka-live `cmd_stop` + furtka `--yes`**

**Goal:** `setka-live stop` pyta o potwierdzenie (zenity) zanim zatrzyma target;
`--yes`/`-y` pomija dialog; bez zenity i bez `--yes` → odmowa z komunikatem.
`restart` pozostaje nietknięty.

**Requirements:** R-new-3, R-new-4

**Dependencies:** Brak (`ZENITY_BIN`/`NOTIFY_BIN` już zadeklarowane).

**Files:**
- Modify: `deploy/live/bin/setka-live` (`cmd_stop`, parsowanie argów `stop` w
  `main()`, `usage()`)
- Test: `deploy/live/tests/test_setka_live.sh`

**Approach:**
- `cmd_stop` przyjmuje informację o fladze `--yes` (parsowanie w `main()` dla
  podkomendy `stop`, analogicznie do reszty `case`).
- Gdy `--yes` → od razu `sctl stop "$TARGET"` (zachowanie sprzed zmiany).
- Bez `--yes`:
  - jeśli `command -v "$ZENITY_BIN"` → dialog `--question --default-cancel
    --icon=dialog-warning --title=... --text=...` ostrzegający, że zatrzymanie
    ubije OBS/Bitwig/kiosk i przerwie ewentualne nagranie; `rc != 0 →
    log "Anulowano zatrzymanie warstwy" + return 0` (fail-safe); `rc == 0 →
    sctl stop "$TARGET"` + opcjonalny `notify-send`.
  - jeśli brak zenity → `err` z komunikatem „Brak zenity — użyj `setka-live stop
    --yes`, by potwierdzić w terminalu." + `return 1` (nie zatrzymuj po cichu).
- **Nie zmieniać `cmd_restart`** — woła `sctl stop` bezpośrednio, świadomie omija
  bramkę.

**Execution note:** Test-first — najpierw dopisać/zaktualizować przypadki w
`test_setka_live.sh` (cancel = brak `stop` w REC_LOG; potwierdzenie = jest stop;
`--yes` = jest stop bez wywołania zenity; restart wciąż zawiera stop target),
potem zmienić `cmd_stop`. To komenda współdzielona z istniejącym testem — bramka
musi nie zepsuć invariantów restartu.

**Patterns to follow:**
- `cmd_delete_last` — struktura bramki zenity (`command -v`, `--question
  --default-cancel`, fail-safe na cancel, `NOTIFY_BIN` best-effort).
- Harness `run_setka` / `run_delete_last` w `test_setka_live.sh` — wstrzykiwanie
  `ZENITY_BIN="$ZENITY_REC"` + `ZENITY_RC`.

**Test scenarios:**
- Happy path: `stop` z zenity zwracającym 0 (potwierdzone) → REC_LOG zawiera
  `--user stop live-recording.target`, exit 0.
- Error/fail-safe: `stop` z zenity zwracającym !=0 (anulowano) → REC_LOG **nie**
  zawiera `stop live-recording.target`, exit 0, log „Anulowano".
- Happy path (bypass): `stop --yes` → REC_LOG zawiera stop target, zenity-rec
  **niewywołany** (brak wpisu w `ZENITY_LOG`), exit 0.
- Error path: `stop` bez zenity (`ZENITY_BIN` wskazuje nieistniejące) i bez
  `--yes` → exit !=0, REC_LOG bez stop target, komunikat wskazuje `--yes`.
- Regression/integration: `restart` (linie ~56-75) wciąż zawiera stop+start
  targetu we właściwej kolejności i obejmuje `live-preflight.service` — bramka
  `cmd_stop` go NIE dotyka (woła `sctl stop` bezpośrednio).
- Regression: `start` (auto-layout, best-effort) bez zmian — wciąż zielony.
- Edge: aktualizacja istniejącego testu `stop` (linie ~50-54), tak by wstrzykiwał
  zenity-stub i pozostał zielony (nie usuwać invariantu „woła stop target").

**Verification:**
- `deploy/live/tests/test_setka_live.sh` zielony (wszystkie przypadki, w tym
  niezmienione start/restart/delete-last).

- [x] **Unit 3: Dokumentacja (README warstwy live)**

**Goal:** README opisuje nowe pozycje menu traya i nową semantykę `stop`
(potwierdzenie + `--yes`).

**Requirements:** R-new-1, R-new-2, R-new-3 (dokumentacja)

**Dependencies:** Unit 1, Unit 2 (opisujemy faktyczne zachowanie).

**Files:**
- Modify: `deploy/live/README.md` (sekcja „Ikona tray i autostart", linie ~176-180;
  oraz blok użycia komend `stop`, linie ~32-34)

**Approach:**
- W „Menu traya" dopisać dwie pozycje na górze listy: **Uruchom warstwę live** →
  `setka-live start`, **Zatrzymaj warstwę live** → `setka-live stop`
  (z adnotacją: pyta o potwierdzenie).
- Przy opisie `setka-live stop` dodać wzmiankę o potwierdzeniu zenity i fladze
  `--yes` (skrypty/headless).
- Zsynchronizować tekst `usage()` z README (oba miejsca opisują `stop`).

**Patterns to follow:**
- Istniejący format listy „Menu traya" i tabel komend w README.

**Test scenarios:**
- Brak testów automatycznych (dokumentacja). Weryfikacja manualna: lista menu w
  README odpowiada `build_menu_items()`; opis `stop` zgodny z `cmd_stop`/`usage()`.

**Verification:**
- README i `usage()` opisują ten sam zestaw zachowań co kod (brak dryfu doc↔kod).

## System-Wide Impact

- **Interaction graph:** `setka-tray` (menu) → `setka-live start|stop`. `cmd_stop`
  współdzielony przez tray + terminal + (potencjalnie) skróty. `cmd_restart` woła
  `sctl stop` z pominięciem `cmd_stop` — celowo poza bramką.
- **Error propagation:** cancel zenity → fail-safe `return 0` (brak akcji, log).
  Brak zenity bez `--yes` → `return 1` z komunikatem. Błąd `sctl` propaguje exit.
- **State lifecycle risks:** `stop` ubija `live-recording.target` w tym
  `obs.service` — bramka chroni przed przypadkowym przerwaniem nagrania. Operacja
  odwracalna przez `start`.
- **API surface parity:** zmiana kontraktu CLI `setka-live stop` (zaczyna pytać /
  nowa flaga `--yes`). Dotyczy wszystkich konsumentów `stop`; `restart` bez zmian.
  Skróty GNOME nie wołają `stop`, więc bez wpływu.
- **Integration coverage:** test bash potwierdza, że bramka `cmd_stop` nie zmienia
  zachowania `restart` (który nie przechodzi przez `cmd_stop`).

## Risks & Dependencies

- **Regresja istniejącego testu `stop`** — najwyższe ryzyko. Po dodaniu bramki
  `run_setka stop` bez zenity-stuba zmieni zachowanie. Mitygacja: zaktualizować
  ten przypadek (Unit 2) i wykonać test-first.
- **Hard-gate na zenity blokowałby headless stop** — mitygacja: flaga `--yes`.
- **Zależność od zenity/notify-send** — zweryfikowane na maszynie docelowej w
  origin-doc (zenity 4.0.1, notify-send 0.8.3). GNOME/X11.

## Documentation / Operational Notes

- README warstwy live + `usage()` aktualizowane w Unit 3 (jedno źródło opisu
  komend rozjeżdża się łatwo — zsynchronizować oba).
- Instalacja bez zmian: `setka-tray` instalowany przez `deploy/live/install.sh`;
  nowe pozycje menu są w kodzie, nie wymagają zmiany instalatora.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md](docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md)
  (Deferred to Planning: launcher a `restart`/`status`)
- Kod: `deploy/live/bin/setka-tray` (`build_menu_items`), `deploy/live/bin/setka-live`
  (`cmd_stop`, `cmd_restart`, `cmd_delete_last`, `usage`)
- Testy: `deploy/live/tests/test_setka_tray.py`, `deploy/live/tests/test_setka_live.sh`
- Dokumentacja: `deploy/live/README.md` (sekcje „Ikona tray", użycie komend)
- Learnings: `[[gnome-keybinding-clean-env]]`, `[[cinemon-fermata-preset-drift]]`
