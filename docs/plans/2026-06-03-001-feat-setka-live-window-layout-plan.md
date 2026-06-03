---
title: "feat: setka-live show — wyciągnięcie i ułożenie okien na dwóch monitorach"
type: feat
status: completed
date: 2026-06-03
origin: docs/brainstorms/2026-06-03-setka-live-window-layout-requirements.md
---

# feat: setka-live show — wyciągnięcie i ułożenie okien na dwóch monitorach

## Overview

Dodajemy do warstwy live komendę `setka-live show`, która wyciąga na wierzch i układa okna
OBS, Bitwiga i kiosku Paternologii w stałym układzie na dwóch monitorach (Bitwig — cały lewy
ekran; OBS — górna połowa prawego; Paternologia — dolna połowa prawego). `setka-live start`
wywołuje to samo układanie na końcu (best-effort). Realizacja przez `wmctrl` (EWMH na
GNOME/Xorg), z geometrią liczoną na żywo z `xrandr` — nic nie jest zaszyte na sztywno.

## Problem Frame

Po `setka-live start` środowisko działa, ale okna lądują w przypadkowych miejscach / pod
sobą; operator musi ręcznie je rozkładać przed nagraniem, co psuje obietnicę „jednego
polecenia". (see origin: docs/brainstorms/2026-06-03-setka-live-window-layout-requirements.md)

## Requirements Trace

- R1. `setka-live show` wyciąga na wierzch i układa OBS, Bitwiga i kiosk w stałym układzie.
- R2. Układ: **lewy monitor** (najmniejszy offset X) — Bitwig na całość; **prawy monitor** —
  OBS górna połowa, Paternologia dolna połowa.
- R3. `setka-live start` na końcu wykonuje to samo układanie (best-effort), a `show` jest też
  dostępne osobno.
- R4. Idempotencja — wielokrotne wywołanie daje ten sam układ.
- R5. Brak okna nie wywraca komendy: układa to, co istnieje, raportuje brakujące; twardy błąd
  tylko dla realnych awarii środowiska (brak DISPLAY / wmctrl / sesja nie-X11).

## Scope Boundaries

- Brak obsługi Waylanda — maszyna to GNOME na Xorg (`XDG_SESSION_TYPE=x11`, realny Xorg, brak
  Xwaylanda). Komenda ma jawnie odmówić na nie-X11, nie udawać sukcesu.
- Brak dynamicznej konfiguracji liczby/rozdzielczości monitorów ani profili `xrandr`; geometria
  czytana z `xrandr` pod obecny zestaw 2 monitorów.
- Nie ruszamy paternologia.service ani warstwy audio — czysto okienkowa nakładka.
- Brak GUI/konfiguratora układów; jeden zaszyty układ (R2).

## Context & Research

### Relevant Code and Patterns

- `deploy/live/bin/live-preflight.sh` — **wzorzec architektoniczny do skopiowania**: czyste
  funkcje decyzyjne karmione tekstem (`preflight_rate_ok` parsuje `pw-metadata`), `poll_ok`
  z grace-timeoutem (retry bez wiszenia), live-wrappery pobierające świeże dane, i source-guard
  `if [ "${BASH_SOURCE[0]}" = "${0}" ]; then main "$@"; fi` umożliwiający sourcing w testach.
- `deploy/live/bin/setka-live` — dyspozytor `case` z `usage()`; indirekcja `SYSTEMCTL_BIN`
  (env override wyłącznie dla testów). `cmd_start` to obecnie `sctl start "$TARGET"`.
- `deploy/live/bin/paternologia-kiosk.sh` — wywołanie `brave --kiosk … --user-data-dir=…`;
  dodamy `--class=setka-kiosk` dla pewnego, unikalnego uchwytu okna.
- `deploy/live/install.sh` — `install_file()` idempotentny (`cmp -s`, backup `.bak-STAMP`),
  pętla po `bin/*` (nowy skrypt skopiuje się automatycznie), ostrzeżenia niefatalne.
- `deploy/live/tests/test_setka_live.sh` — wzorzec testu: rejestrator-recorder podstawiany pod
  `SYSTEMCTL_BIN`, log wywołań, liczniki `pass/fail`, asercje `grep` na realnych argumentach.

### Institutional Learnings

- `docs/solutions/2026-06-01-bitwig-pipewire-44100-usb-audio-contention.md` i
  `…bitwig-alsa-seq-invisible-virmidi-bridge.md` — dotyczą audio/MIDI, nie okien; bez wpływu
  na ten plan (potwierdzono brak kolizji zakresu).
- Pamięć projektu: maszyna dev to **X11** (`DISPLAY=:1` w activation env), `bats` niedostępny →
  testy w czystym bashu. Warstwa live celowo nie tyka PipeWire/paternologii.

### External References

- Pominięte świadomie — `wmctrl`/EWMH/`xrandr` to dojrzałe, stabilne narzędzia, a lokalny
  wzorzec (live-preflight) jest bezpośrednio przekładalny. Brak ryzyka uzasadniającego badania.

## Key Technical Decisions

- **`wmctrl`, nie GNOME Shell Eval**: Mutter/Xorg w pełni wspiera EWMH; `gnome-shell Eval`
  zablokowany (zwraca `false`). `wmctrl -lx` listuje okna z WM_CLASS, `-r <cls> -e g,x,y,w,h`
  ustawia geometrię, `-a` aktywuje. (Alternatywa `xdotool` równoważna; `wmctrl` zwięźlejszy dla
  „ustaw geometrię po klasie".)
- **Identyfikacja monitorów po offsecie X, nie po nazwie**: lewy = najmniejszy Xoffset, prawy =
  większy. Przeżyje zamianę kabli/nazw (HDMI/DVI). Geometria z `xrandr --listmonitors`.
- **Kiosk dostaje własny `--class=setka-kiosk`**: deterministyczny, unikalny uchwyt — nie
  zderza się ze zwykłym Brave operatora. OBS i Bitwig dopasowywane po ich natywnym WM_CLASS
  (dokładne wartości do potwierdzenia — patrz Deferred).
- **Rozdzielenie czyste/live jak w preflight**: funkcje parsujące `xrandr` i liczące prostokąty
  slotów są czyste i testowalne tekstem; wywołania `wmctrl` w warstwie live za indirekcją
  `WMCTRL_BIN` (recorder w testach).
- **Auto-layout po `start` jest best-effort**: nie wolno mu wywrócić `start` (R3, R5). Pętla
  „czekaj aż okno istnieje" z grace-timeoutem pokrywa opóźnione pojawianie się okien
  (flatpak Bitwig, kiosk czekający na /health), wzorowana na `poll_ok`.

## Open Questions

### Resolved During Planning

- Nazwa komendy → `show` (decyzja z brainstormu).
- Czy `start` układa automatycznie → tak, na końcu, best-effort; `show` też ręcznie.
- Jak liczyć geometrię → z `xrandr --listmonitors`, sortując sloty po offsecie X.
- Czym targetować kiosk → własny `--class=setka-kiosk`.

### Deferred to Implementation — rozstrzygnięte na żywo (2026-06-03)

- **Dokładne WM_CLASS dla OBS i Bitwiga-flatpak** — ✅ POTWIERDZONE `wmctrl -lx` przy żywych
  oknach: OBS = `obs.obs`, Bitwig-flatpak = `com.bitwig.BitwigStudio` (dokładnie domyślne stałe).
  Konfigurowalne env-override na górze `live-layout.sh`.
- **Zdjęcie maksymalizacji przed geometrią** — ✅ zaimplementowane (`-b remove,maximized_*` przed
  `-e`); działa.
- **Kompensacja `_NET_FRAME_EXTENTS`** — ⚠️ zbadane: Bitwig (CSD, brak ramek) trafia 1:1; OBS ma
  `gravity: Static`, ramkę top 37 px i WYMUSZONY min-rozmiar przez zadokowane panele → ląduje w
  prawym górnym obszarze z offsetem (~+118 px y), którego sama korekta ramki nie zlikwiduje.
  Decyzja (potwierdzona z operatorem): zostawiamy — to ograniczenie OBS/Muttera, nie błąd; okno
  jest wyciągnięte i widoczne. Udokumentowane w README jako znana pułapka.
- **Dobór wartości grace-timeoutu** — domyślne 10 s, env-override; przy `show` z żywymi oknami
  predykat-prawda zwraca natychmiast (zweryfikowane). Finalny dobór przy `start` z zimnego startu
  pozostaje do obserwacji operacyjnej.

## High-Level Technical Design

> *Ilustruje zamierzony kształt rozwiązania — wskazówka kierunkowa do recenzji, nie specyfikacja
> implementacji. Agent implementujący traktuje to jako kontekst, nie kod do przepisania.*

Przepływ `setka-live show`:

```
1. Bramki środowiska (twardy FAIL → exit !=0):
     XDG_SESSION_TYPE=x11 ?  DISPLAY ustawiony ?  wmctrl obecny ?
2. monitors = parse(xrandr --listmonitors)          # czysta funkcja
     → [ {x,y,w,h}, … ] posortowane po offsecie X
     LEWY = monitors[0], PRAWY = monitors[1]
3. sloty = compute_slots(LEWY, PRAWY)               # czysta funkcja
     bitwig      = LEWY  (cały)
     obs         = PRAWY górna połowa  (h/2)
     paternologia= PRAWY dolna połowa  (y+h/2, h/2)
4. dla każdego (WM_CLASS → slot):
     poll_window_exists(cls, grace)                  # czeka na okno; brak → pomiń+raportuj (R5)
     wmctrl: remove maximized → -e 0,x,y,w,h → -a    # ustaw geometrię + na wierzch
5. raport: ułożone / brakujące; exit 0 gdy tylko brak okien
```

Mapowanie geometrii dla obecnego sprzętu (poglądowo, liczone na żywo):
- LEWY  (DVI, 1280x1024 @ +0+0):     Bitwig       → 0,0,1280,1024
- PRAWY (HDMI, 1440x900 @ +1280+0):  OBS          → 1280,0,1440,450
                                     Paternologia → 1280,450,1440,450

## Implementation Units

- [x] **Unit 1: Deterministyczny uchwyt okna kiosku**

**Goal:** Kiosk Paternologii dostaje stały, unikalny WM_CLASS do pewnego targetowania.

**Requirements:** R1, R4

**Dependencies:** brak

**Files:**
- Modify: `deploy/live/bin/paternologia-kiosk.sh`
- Test: `deploy/live/tests/test_kiosk_class.sh` (nowy)

**Approach:**
- Dodać `--class=setka-kiosk` do wywołania `brave --kiosk …`. Zachować istniejące flagi i
  `--user-data-dir`. Zaktualizować komentarz ABOUTME/inline o roli klasy w układaniu okien.

**Patterns to follow:**
- Istniejące wywołanie `exec brave …` w tym samym pliku.

**Test scenarios:**
- Happy path: skrypt zawiera `--class=setka-kiosk` (grep na pliku — czysto statyczne, bez
  uruchamiania brave, bo to NO mock i nie chcemy realnego okna w teście).
- Edge case: nadal zawiera `--kiosk` i `--user-data-dir` (regresja — nie zgubić istniejących flag).

**Verification:**
- `grep` potwierdza obecność `--class=setka-kiosk` obok dotychczasowych flag; reszta skryptu
  nietknięta.

---

- [x] **Unit 2: Czyste funkcje geometrii (`live-layout.sh` rdzeń)**

**Goal:** Parsowanie `xrandr --listmonitors` → uporządkowane monitory i obliczenie prostokątów
slotów (bitwig/obs/paternologia) — testowalne wyłącznie tekstem.

**Requirements:** R2, R4

**Dependencies:** brak

**Files:**
- Create: `deploy/live/bin/live-layout.sh` (sekcja czystych funkcji + source-guard; bez `main` na razie)
- Test: `deploy/live/tests/test_live_layout.sh` (nowy)

**Execution note:** Test-first — najpierw failing test parsera na utrwalonym wyjściu `xrandr`.

**Approach:**
- `layout_parse_monitors "<xrandr --listmonitors>"` → wypisuje linie `x y w h` posortowane
  rosnąco po `x`. Token `1440/530x900/300+1280+0` → w=1440, h=900, x=1280, y=0 (ignorować mm).
- `layout_slot_bitwig`, `layout_slot_obs`, `layout_slot_paternologia` przyjmują geometrie lewego
  i prawego monitora i zwracają `x y w h` slotu (obs = górna połowa, paternologia = dolna połowa
  prawego; bitwig = cały lewy). Dzielenie wysokości całkowite (`h/2`); dolna połowa bierze resztę.
- Stałe WM_CLASS jako zmienne na górze pliku (placeholdery do potwierdzenia w Unit 3/Deferred),
  `KIOSK_CLASS=setka-kiosk` ustalone.
- Source-guard na końcu (jak w `live-preflight.sh`).

**Patterns to follow:**
- `deploy/live/bin/live-preflight.sh` — czyste funkcje + source-guard.
- `deploy/live/tests/test_live_preflight.sh` — karmienie funkcji utrwalonym tekstem, liczniki pass/fail.

**Test scenarios:**
- Happy path: wejście z realnego `xrandr` (2 monitory) → `layout_parse_monitors` zwraca dokładnie
  `0 0 1280 1024` oraz `1280 0 1440 900`, w tej kolejności (lewy przed prawym).
- Happy path: `layout_slot_obs(1280 0 1440 900)` → `1280 0 1440 450`; `layout_slot_paternologia`
  → `1280 450 1440 450`; `layout_slot_bitwig(0 0 1280 1024)` → `0 0 1280 1024`.
- Edge case: nieparzysta wysokość prawego monitora (np. 901) → suma połówek == pełna wysokość
  (brak zgubionego piksela: górna 450 + dolna 451 lub odwrotnie, ale styk bez dziury/zakładki).
- Edge case: monitory podane w odwrotnej kolejności w wejściu → sortowanie po X i tak daje
  lewy=offset 0 jako pierwszy.

**Verification:**
- `bash deploy/live/tests/test_live_layout.sh` zielony; funkcje liczą prostokąty zgodne z R2 dla
  realnej geometrii i dla syntetycznych przypadków brzegowych.

---

- [x] **Unit 3: Warstwa live + `main` (`live-layout.sh`)**

**Goal:** Realne wyciąganie i układanie okien przez `wmctrl`, z bramkami środowiska, pollingiem
pojawienia się okien i miękką obsługą braku okna.

**Requirements:** R1, R2, R3, R5

**Dependencies:** Unit 2

**Files:**
- Modify: `deploy/live/bin/live-layout.sh` (live-wrappery + `main`)
- Test: `deploy/live/tests/test_live_layout.sh` (rozszerzenie o ścieżkę live z recorderem)

**Approach:**
- Indirekcje: `WMCTRL_BIN="${WMCTRL_BIN:-wmctrl}"`, `XRANDR_BIN="${XRANDR_BIN:-xrandr}"` (env
  override dla testów — wzorzec `SYSTEMCTL_BIN`).
- Bramki na starcie `main` (twardy FAIL, exit !=0, czytelny komunikat): sesja `XDG_SESSION_TYPE`
  ≠ `x11` → odmowa; brak `DISPLAY` → odmowa; brak `wmctrl` w PATH → odmowa z podpowiedzią instalacji.
- `layout_window_exists(cls)` przez `wmctrl -lx` (grep po klasie); `poll_window_exists(cls,grace)`
  wzorowane na `poll_ok` z `live-preflight.sh`.
- `layout_place(cls, x y w h)`: zdejmij maksymalizację (`-b remove,maximized_*`), ustaw geometrię
  (`-e 0,x,y,w,h`), aktywuj (`-a`). Kolejność i ewentualna korekta ramki — patrz Deferred.
- `main`: czyta monitory (`XRANDR_BIN --listmonitors`), liczy sloty (Unit 2), iteruje po
  mapie `WM_CLASS→slot`; brakujące okno → log + kontynuacja, na końcu raport „ułożone/brakujące";
  exit 0 gdy jedyny problem to brak okien (R5).

**Execution note:** Test-first dla bramek i logiki braku-okna; `wmctrl` przez recorder, NIE mock
realnego WM (zero realnych okien w teście).

**Patterns to follow:**
- `live-preflight.sh`: `poll_ok`, live-wrappery, `log/err`, source-guard.
- `test_setka_live.sh`: recorder podstawiany pod binarkę, asercje `grep` na argumentach.

**Test scenarios:**
- Happy path (recorder): przy „istniejących" oknach (recorder `wmctrl -lx` zwraca 3 klasy)
  `main` woła `-e` z prostokątami zgodnymi z R2 dla każdej klasy oraz `-a` (na wierzch).
- Integration (cross-layer): `main` faktycznie spina parser geometrii (Unit 2) z wywołaniami
  `wmctrl` — recorder loguje współrzędne wyliczone z podstawionego `XRANDR_BIN`, nie zaszyte.
- Error path: `XDG_SESSION_TYPE=wayland` → exit !=0, komunikat o braku wsparcia, ZERO wywołań `wmctrl`.
- Error path: `WMCTRL_BIN` wskazuje nieistniejącą binarkę / brak w PATH → exit !=0 z podpowiedzią.
- Edge case (R5): recorder `-lx` nie zwraca klasy Bitwiga → pozostałe dwa okna ułożone, Bitwig
  raportowany jako brakujący, exit 0.
- Idempotencja (R4): dwa kolejne przebiegi `main` generują identyczny zestaw wywołań geometrii.

**Verification:**
- `bash deploy/live/tests/test_live_layout.sh` zielony; na żywej maszynie `live-layout.sh` układa
  realne okna zgodnie z R2 (weryfikacja manualna po dostrojeniu WM_CLASS/ramek z Deferred).

---

- [x] **Unit 4: Wpięcie w `setka-live` (komenda `show` + auto po `start`)**

**Goal:** `setka-live show` woła layout; `setka-live start` układa na końcu best-effort; `usage`
zaktualizowane.

**Requirements:** R1, R3, R5

**Dependencies:** Unit 3

**Files:**
- Modify: `deploy/live/bin/setka-live`
- Test: `deploy/live/tests/test_setka_live.sh` (rozszerzenie)

**Approach:**
- `LAYOUT_BIN="${LAYOUT_BIN:-$(dirname "$0")/live-layout.sh}"` — lokalizacja siostrzanego skryptu,
  env override dla testów (wzorzec `SYSTEMCTL_BIN`).
- `cmd_show() { "$LAYOUT_BIN"; }`.
- `cmd_start`: po `sctl start "$TARGET"` dołożyć best-effort `"$LAYOUT_BIN" || true` (layout nie
  może wywrócić startu — R3/R5). Rozważyć krótki komunikat, że układanie jest best-effort.
- `case` + `usage()`: dodać `show` z opisem; zachować pozostałe komendy bez zmian.

**Patterns to follow:**
- Istniejący `case`/`usage`/`cmd_*` w `setka-live`; indirekcja `SYSTEMCTL_BIN` → analogiczne `LAYOUT_BIN`.

**Test scenarios:**
- Happy path: `setka-live show` woła `LAYOUT_BIN` (recorder odnotowuje 1 wywołanie), exit 0.
- Happy path/Integration: `setka-live start` woła `start live-recording.target` ORAZ następnie
  `LAYOUT_BIN`, w tej kolejności (layout po starcie targetu).
- Error path (R3/R5): `LAYOUT_BIN` zwraca !=0 → `setka-live start` mimo to kończy się exit 0
  (układanie best-effort nie wywraca startu).
- Regresja: niezmienione inwarianty `restart` (nadal `stop`+`start`, nigdy `restart <target>`,
  stop obejmuje `live-preflight`); żadna komenda nadal nie dotyka `paternologia`.
- Edge case: nieznana komenda → niezerowy exit + `usage` (istniejąca asercja utrzymana).

**Verification:**
- `bash deploy/live/tests/test_setka_live.sh` zielony, łącznie z nowymi asercjami `show`/`start→layout`
  i zachowanymi inwariantami restartu/paternologii.

---

- [x] **Unit 5: Zależność `wmctrl` w instalatorze + dokumentacja**

**Goal:** Instalacja sprawdza obecność `wmctrl` i podpowiada instalację; README i CLAUDE.md
opisują `setka-live show`.

**Requirements:** R1, R5

**Dependencies:** Unit 4

**Files:**
- Modify: `deploy/live/install.sh`
- Modify: `deploy/live/README.md`
- Modify: `CLAUDE.md` (sekcja workflow / tabela komend live)
- Test: `deploy/live/tests/test_install.sh` (rozszerzenie)

**Approach:**
- `live-layout.sh` skopiuje się automatycznie (pętla `bin/*` w `install.sh` — bez zmian tam).
- Dodać niefatalne sprawdzenie `command -v wmctrl` (wzorzec ostrzeżenia o PATH): brak → wypisz
  „zainstaluj: sudo apt install wmctrl", ale NIE przerywaj instalacji (FAIL FAST dotyczy błędów
  krytycznych; brak narzędzia okiennego nie blokuje instalacji unitów/skryptów audio-MIDI).
- README: dopisać `show` do tabeli komend + krótki opis układu (R2) i pułapek (Wayland, ramki).
- CLAUDE.md: w opisie warstwy live dopisać `setka-live show`.

**Patterns to follow:**
- `install.sh` — istniejące niefatalne ostrzeżenie o PATH (`case ":$PATH:" …`).
- `test_install.sh` — istniejące asercje kopiowania do `BIN_DIR` z env override.

**Test scenarios:**
- Happy path: po `install.sh` `live-layout.sh` jest obecny w `BIN_DIR` z trybem 0755.
- Edge case (idempotencja): druga instalacja bez zmian treści → „bez zmian" dla `live-layout.sh`
  (asercja na braku zbędnego backupu — wzorzec istniejących testów).
- Error path (niefatalność): brak `wmctrl` w PATH NIE powoduje niezerowego exitu `install.sh`
  (symulować przez okrojony `PATH`/stub `command`); ostrzeżenie obecne w wyjściu.

**Verification:**
- `bash deploy/live/tests/test_install.sh` zielony; README i CLAUDE.md wymieniają `setka-live show`.

## System-Wide Impact

- **Interaction graph:** Nowy skrypt `live-layout.sh` wołany z `setka-live` (`show` i koniec
  `start`). `start` zależy od warstwy systemd (uruchamia okna), ale layout działa na poziomie
  EWMH/X11 — nie dotyka systemd, paternologii ani audio.
- **Error propagation:** Layout w `start` jest best-effort (`|| true`) — jego błąd nie może
  wywrócić startu (R3/R5). Bezpośrednie `show` zwraca niezerowo tylko dla awarii środowiska
  (brak DISPLAY/wmctrl, nie-X11), nie dla brakującego okna.
- **State lifecycle risks:** Brak trwałego stanu — operacja czysto okienkowa, w pełni
  idempotentna (R4). Powtórzenie nadpisuje geometrię tymi samymi wartościami.
- **API surface parity:** Powierzchnia CLI `setka-live` rośnie o `show`; `usage`, README i
  CLAUDE.md muszą wymienić ją spójnie (Unit 4/5).
- **Integration coverage:** Test integracyjny w Unit 3 (parser geometrii → realne argumenty
  `wmctrl` przez recorder) oraz w Unit 4 (`start` → `start target` → `LAYOUT_BIN` w kolejności)
  pokrywają styki, których same testy jednostkowe nie udowodnią.

## Risks & Dependencies

- **WM_CLASS OBS/Bitwiga niepewne do czasu probowania** — mitigacja: konfigurowalne stałe na górze
  `live-layout.sh`, wartości potwierdzone `wmctrl -lx` przy żywych oknach (Deferred); R5 sprawia,
  że błędne dopasowanie degraduje się do „okno pominięte", nie do crasha.
- **Kompensacja ramek (`_NET_FRAME_EXTENTS`) na Mutterze** — ryzyko offsetu o kilka px; mitigacja:
  empiryczna weryfikacja i ewentualna korekta w `layout_place` (Deferred).
- **Zależność `wmctrl`** — nie zainstalowany; mitigacja: niefatalne sprawdzenie w instalatorze +
  bramka w `live-layout.sh` z czytelną podpowiedzią `apt install wmctrl`.
- **Przyszłe przejście na Wayland** — `wmctrl` przestanie działać; mitigacja: jawna bramka
  `XDG_SESSION_TYPE=x11` odmawia czytelnie zamiast cicho zawodzić.

## Documentation / Operational Notes

- README warstwy live: tabela komend + opis układu R2 i pułapek (Wayland, ramki, WM_CLASS).
- CLAUDE.md: dopisać `setka-live show` w opisie warstwy live.
- Operacyjnie: brak wpływu na nagrywanie/audio; komenda działa tylko w aktywnej sesji graficznej
  operatora (DISPLAY z activation env). Weryfikacja manualna po instalacji: `setka-live show`
  układa realne okna zgodnie z R2.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-03-setka-live-window-layout-requirements.md](docs/brainstorms/2026-06-03-setka-live-window-layout-requirements.md)
- Wzorce: `deploy/live/bin/live-preflight.sh`, `deploy/live/bin/setka-live`,
  `deploy/live/bin/paternologia-kiosk.sh`, `deploy/live/install.sh`,
  `deploy/live/tests/test_setka_live.sh`, `deploy/live/tests/test_live_preflight.sh`
- Sprzęt (zweryfikowane `xrandr --listmonitors`): DVI-D-0 1280x1024 @ +0+0 (lewy),
  HDMI-0 1440x900 @ +1280+0 (prawy); sesja `XDG_SESSION_TYPE=x11`, realny Xorg.
