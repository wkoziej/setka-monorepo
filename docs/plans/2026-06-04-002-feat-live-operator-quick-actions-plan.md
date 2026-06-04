---
title: "feat: Szybkie akcje operatorskie sesji live (launcher + przenieś ostatnie nagranie do kosza)"
type: feat
status: completed
date: 2026-06-04
deepened: 2026-06-04
reworked: 2026-06-04
origin: docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md
---

# feat: Szybkie akcje operatorskie sesji live (launcher + przenieś ostatnie nagranie do kosza)

> **Przeróbka 2026-06-04 (podczas /ce:work — ustalanie niewiadomych).** Badanie realnego
> środowiska + doprecyzowanie operatora zmieniły rdzeń planu. Najważniejsze: (1) kasujemy
> **cały katalog nagrania**, nie pojedynczy plik; (2) **przez przeniesienie do kosza**
> (`gio trash`), odwracalnie, nie `rm`; (3) root nagrań z **env `SETKA_RECORDINGS_ROOT`**
> (`~/Wideo/obs`), **nie z OBS WebSocket**; (4) skoro OBS jest zbędny, **logika żyje w bashu
> `setka-live`, nie w paternologii** — co usuwa dawne Unity 1 i 2 (endpoint + cleanup +
> `obs_client`). Poprzednia wersja planu (paternologia HTTP + usuwanie pliku `.mkv` + sidecar +
> kontrakt TOCTOU) jest **nieaktualna** i została zastąpiona poniższą.

## Overview

Dodajemy operatorowi sesji live dwa szybkie, globalne sposoby na akcje spoza przepływu
nagrywania: (1) przywrócenie układu okien przez istniejące `setka-live show`, (2) przeniesienie
ostatniego nagrania do kosza (`setka-live delete-last`) z potwierdzeniem i informacją zwrotną.
Obie akcje są wyzwalane podwójnie — ikoną w system tray (menu) **oraz** globalnymi skrótami
GNOME — a oba wyzwalacze wołają te same podkomendy `setka-live` (jedno źródło prawdy).

Logika „usuń ostatnie" to **czysty bash** w `setka-live`: ustal root nagrań (env, z defaultem
`~/Wideo/obs`), znajdź najnowszy prawidłowy katalog nagrania, opisz go (nazwa + wiek + rozmiar),
potwierdź (`zenity`), przenieś do kosza GNOME (`gio trash`), powiadom (`notify-send`). Operacja
jest **odwracalna** (przywrócenie z Kosza/Nautilusa), więc nie potrzebuje ciężkiej maszynerii
guardów ani połączenia z OBS.

Reset rigu (Bitwig clear + re-wybór patternów na M:S/Freak/Boss) jest **poza zakresem** tej
iteracji (origin: R7) i zaplanowany jako osobna, późniejsza faza.

## Problem Frame

Podczas sesji nagraniowej (warstwa `setka-live`: Bitwig + OBS + kiosk paternologii na dwóch
monitorach X11) operator musi czasem wykonać akcję między ujęciami bez schodzenia do terminala:

- `setka-live show` to akcja ratunkowa na rozjechane okna — wyzwalacz musi działać globalnie,
  niezależnie od tego, co jest na wierzchu (przycisk w zakopanym oknie kiosku byłby bezużyteczny).
- „Usuń ostatnie nagranie" — gdy ujęcie się nie udało, operator chce usunąć **całe** nieudane
  nagranie (folder), żeby nie zaśmiecać sesji; jako akcja potencjalnie kosztowna ma być
  **odwracalna** (kosz) i potwierdzona.

Obie akcje wykonywane są z wolnymi rękami i wzrokiem na ekranie (nie w trakcie grania).
(Pełny kontekst — see origin: docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md)

## Requirements Trace

- **R1.** Globalny wyzwalacz dostępny niezależnie od aktywnego okna — realizowany podwójnie:
  ikona w tray z menu **oraz** globalne skróty GNOME. Środowisko: GNOME na X11.
- **R2.** Akcja „pokaż okna" wywołuje `setka-live show` (fire-and-forget; rezultat widać na ekranie).
- **R3.** Akcja „usuń ostatnie nagranie" przenosi **cały najnowszy katalog nagrania** (folder
  `<timestamp>/` w roocie nagrań — wideo + `metadata.json` + `extracted/`/`analysis/`/`blender/`)
  **do kosza GNOME** (`gio trash`), odwracalnie. „Najnowszy" = wg mtime spośród prawidłowych
  katalogów nagrań pod rootem.
- **R3a.** Root nagrań z env `SETKA_RECORDINGS_ROOT` (default `~/Wideo/obs`, fallback `~/Videos/obs`).
  **Nie** z OBS WebSocket (`GetRecordDirectory` zwraca `RecFilePath`, np. `/home/wojtas` — surowy
  plik przed reorganizacją, nie root sfolderyzowanych nagrań).
- **R4.** Przeniesienie wyłącznie po jawnym potwierdzeniu (`zenity`) nazywającym konkretny
  **katalog** (nazwa + wiek + łączny rozmiar).
- **R5.** Po przeniesieniu powiadomienie o wyniku (`notify-send`): co trafiło do kosza
  (+ podpowiedź o przywracaniu) / anulowano / brak nagrania / błąd.
- **R6.** Bezpieczeństwo przez **odwracalność** (kosz, nie `rm`) + **walidację celu** (istnieje,
  katalog, ściśle pod rootem, prawidłowa struktura nagrania); brak twardego guardu „OBS nagrywa"
  (nagranie w toku to surowy plik w innej lokalizacji, nie kandydat).
- **R7.** Brak resetu rigu w tej iteracji (poza zakresem — patrz Scope Boundaries).

## Scope Boundaries

- **Brak resetu rigu**: żadnego czyszczenia ścieżek w Bitwigu ani re-wyboru patternów na
  M:S/Freak/Boss. (Osobna przyszła faza.)
- **Przenosimy CAŁY katalog nagrania do kosza** (poprzednia granica „tylko surowy plik"
  świadomie zniesiona). Operacja odwracalna.
- **Brak twardego `rm`** i brak opróżniania kosza przez tę funkcję.
- **Brak utrwalania stanu** „ostatniego nagrania" — identyfikacja po mtime katalogu, bezstanowo.
- **Logika w `setka-live` (bash), nie w paternologii** — OBS/serwer niepotrzebne po
  doprecyzowaniu. Brak zmian w paternologii, OBS WebSocket, MIDI/bridge/kiosk.
- **Tylko GNOME/X11** — bez wsparcia Wayland / innych DE.
- **Tray bez logiki biznesowej** — tray i skróty to wyłącznie wyzwalacze podkomend `setka-live`.

## Context & Research

### Relevant Code and Patterns

- `deploy/live/bin/setka-live` — dispatch podkomend przez `case` w `main()` (linie ~79-86),
  funkcje `cmd_*`, exit 0=ok / 2=unknown. Indirekcja binarek dla testów: `LAYOUT_BIN`,
  `SYSTEMCTL_BIN`. **Wzorzec dla `cmd_delete_last` + nowej indirekcji** (`GIO_BIN`, `ZENITY_BIN`,
  `NOTIFY_BIN`, `SETKA_RECORDINGS_ROOT`).
- `deploy/live/bin/live-layout.sh` — wzorzec: czyste funkcje testowalne tekstem, env z
  defaultami `"${VAR:-default}"`, `log()`/`err()`, twarda bramka X11, best-effort gdy brak
  narzędzia. **Wzorzec dla `live-keybindings.sh`** i dla funkcji w `cmd_delete_last`.
- `deploy/live/install.sh` — idempotentny `install_file()` z `cmp -s` + backup `.bak-<STAMP>`,
  kopiowanie `bin/*` → `~/.local/bin`, wycofywanie starego `.desktop` w `~/.config/autostart`.
  `daemon-reload`/efekty uboczne tylko dla domyślnego katalogu (ochrona testów). **Wzorzec dla
  instalacji `setka-tray`, `.desktop`, skrótów.**
- `deploy/live/tests/test_*.sh` — plain bash (brak bats), recorder-mock binarek przez env,
  liczniki `pass/fail`, `mktemp` + cleanup, source-guard. **Wzorzec dla rozszerzenia
  `test_setka_live.sh`, nowego `test_keybindings.sh`, rozszerzenia `test_install.sh`.**
- `packages/obsession/.../advanced_scene_switcher_extractor.py` (linie 62-121) — **istniejący
  wzorzec „znajdź najnowsze nagranie"**: kandydaci `~/Wideo/obs`, `~/Videos/obs`; iteruje
  podkatalogi; waliduje strukturę (`metadata.json` + plik wideo); wybiera `max` po mtime pliku
  wideo; odrzuca pliki starsze niż 30 s. **Źródło defaultów roota i pojęcia „prawidłowy katalog
  nagrania".**
- `packages/fermata/src-tauri/src/commands/recordings.rs` (linie 30-157) — **prior art kasowania
  nagrania**: root z env `FERMATA_RECORDINGS_PATH` (default `~/Videos/obs-recordings`),
  `delete_recording_impl` waliduje `exists` + `is_dir` na `root/name`, po czym **`remove_dir_all`
  (nieodwracalnie)**. Nasza funkcja jest świadomie bezpieczniejsza (kosz zamiast `rm`); walidacja
  `exists`+`is_dir`+pod-rootem jest dobrym, sprawdzonym wzorcem do odwzorowania.
- `packages/paternologia/src/paternologia/dependencies.py` (linie 15-24) — wzorzec env-override
  (`PATERNOLOGIA_DATA_DIR`): default + `os.environ.get`. Potwierdza konwencję env dla ścieżek.

### Institutional Learnings

- `docs/plans/2026-06-03-001-feat-setka-live-window-layout-plan.md` — EWMH/wmctrl na GNOME/X11,
  twarda bramka Waylanda, wzorzec testów shell (czyste funkcje + recorder-mock).
- `docs/plans/2026-06-02-002-feat-live-session-launcher-plan.md` — idempotentny install z backupem,
  systemd `--user`.

### External References (zweryfikowane na maszynie docelowej: Ubuntu 24.04.4, GNOME 46, X11)

- **Środowisko OBS:** OBS 32.1.2; aktywny profil `live` (z `user.ini`, które w OBS 30+ ma
  pierwszeństwo nad `global.ini`) → `RecFormat2=hybrid_mp4` (pliki `.mp4`), `RecFilePath=/home/wojtas`,
  split wyłączony. Nagrania finalnie reorganizowane w foldery `~/Wideo/obs/<timestamp>/` (świeże
  foldery z dziś potwierdzają, że dzieje się to automatycznie po stopie). Wniosek: root nagrań ≠
  `RecFilePath` → bierzemy go z env, nie z OBS.
- **Kosz:** `gio` 2.80 obecny; backend `gvfs` 1.54 aktywny; `gio trash --list` działa i pokazuje
  istniejące elementy → `gio trash <ścieżka>` przeniesie folder do kosza GNOME (przywracalne z
  Nautilusa).
- **Tray:** PyGObject `3.48.2`; `gi.require_version("Gtk","3.0")` + `gi.require_version(
  "AyatanaAppIndicator3","0.1")` ładują się. `AppIndicator3` (Canonical) **niedostępny** — Ayatana.
  Indicator pod **GTK3** (menu `Gtk.Menu`), wymaga `set_status(ACTIVE)` + menu. Pakiety apt obecne:
  `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1`.
- **Rozszerzenie:** `gnome-shell-extension-appindicator` aktywne (`org.kde.StatusNotifierWatcher`
  na session busie). Preinstalowane na Ubuntu; install.sh robi defensywny check przez `gdbus`.
- **Skróty:** `gsettings` schema `org.gnome.settings-daemon.plugins.media-keys` klucz
  `custom-keybindings` (lista `as`, pusty stan = dosłownie `@as []`) + relocatable
  `...media-keys.custom-keybinding:/<path>/` z `name`/`command`/`binding`. Ścieżka **musi kończyć
  się `/`**. Zmiana działa **bez restartu sesji**. Idempotencja: własne nazwane ścieżki +
  append-if-absent, osobny case na `@as []`.
- **zenity 4.0.1:** `--question` → exit 0 = potwierdzenie; **wszystko != 0** = „nie ruszaj"
  (fail-safe). `--default-cancel` + `--icon=dialog-warning`.
- **notify-send 0.8.3:** sterować widocznością przez `--urgency` (GNOME ignoruje `-t`).

## Key Technical Decisions

- **Logika w czystym bashu `setka-live`, bez paternologii/OBS**: po doprecyzowaniu funkcja
  potrzebuje tylko: root z env, glob katalogów, `gio trash`, `zenity`, `notify-send` — wszystko
  dostępne w bashu. Połączenie OBS było uzasadnione tylko, gdy trzeba było pobrać katalog z OBS i
  sprawdzać `is_recording()`; oba odpadły. (KISS; usuwa cały serwerowy obszar ryzyka.)
- **Przeniesienie do kosza (`gio trash`) zamiast `rm`**: operacja odwracalna → bezpieczeństwo i
  UX bez ciężkich guardów (decyzja operatora: „przesuwaj folder + informuj, bez guard"). Świadomie
  lepsze niż istniejące `remove_dir_all` w fermacie.
- **Root z env `SETKA_RECORDINGS_ROOT`** (default `~/Wideo/obs`, fallback `~/Videos/obs`):
  porównanie plik-vs-env wypadło jednoznacznie na env — to ustalona konwencja u wszystkich
  konsumentów roota (`FERMATA_RECORDINGS_PATH`, `PATERNOLOGIA_DATA_DIR`), nikt nie trzyma roota w
  pliku-configu; env jest też trywialnie testowalny (tmp dir per test) i ustawialny w deploy.
- **„Najnowszy" = katalog nagrania, nie plik**: wybór `max` po mtime spośród bezpośrednich
  podkatalogów roota, które są **prawidłowymi nagraniami** (zawierają `metadata.json` + plik
  wideo) — odwzorowanie walidacji z obsession/fermaty.
- **Tray i skróty wołają te same podkomendy `setka-live`**: jedno źródło prawdy; tray/skróty to
  wyłącznie wyzwalacze. (see origin: Key Decisions.)
- **Tray: PyGObject + GTK3 + AyatanaAppIndicator3**: jedyny działający namespace na 24.04, zero
  nowych zależności apt.
- **Skróty idempotentnie przez `gsettings`**, własne nazwane ścieżki + append-if-absent — nie
  nadpisujemy customów użytkownika; ponowny install = no-op. Domyślne: `Super+Shift+S` (show),
  `Super+Shift+D` (delete-last), konfigurowalne env (`KB_SHOW`, `KB_DELETE`).
- **Lekkie guardy zamiast ciężkich** (bo odwracalne): odmowa, gdy root pusty/nie-katalog/`==$HOME`;
  kandydat musi mieć prawidłową strukturę i `resolved parent == resolved root` (bez symlink-escape).
  Brak kontraktu TOCTOU/`expected_mtime`, brak sidecar-by-stem, brak guardu OBS — niepotrzebne.

## Open Questions

### Resolved During Planning / Work

- Co kasujemy? → **Cały najnowszy katalog nagrania**, przeniesiony do kosza (`gio trash`).
- Skąd root nagrań? → env `SETKA_RECORDINGS_ROOT`, default `~/Wideo/obs`, fallback `~/Videos/obs`.
- Gdzie żyje logika? → **bash w `setka-live`** (OBS/paternologia niepotrzebne).
- Jak potwierdzać/informować? → `zenity --question --default-cancel` (!=0 = nie ruszaj) + `notify-send`.
- Technologia traya/skrótów? → PyGObject GTK3 + AyatanaAppIndicator3; `gsettings` media-keys.
- Domyślne skróty? → `Super+Shift+S` (show), `Super+Shift+D` (delete-last).
- Format/rozszerzenie pliku (poprzednia niewiadoma `.mkv` vs `.mp4`)? → **nieistotne** — operujemy
  na całym folderze; walidacja sprawdza obecność *jakiegokolwiek* pliku wideo, nie konkretne
  rozszerzenie.
- Split recording? → wyłączony w profilu; przy operacji na folderze i tak bez znaczenia.

### Deferred to Implementation

- **Dokładny zestaw rozszerzeń wideo** uznawanych za „plik wideo" w walidacji katalogu —
  pragmatycznie `*.mp4 *.mkv *.mov *.flv` (env-konfigurowalne, np. `REC_VIDEO_GLOBS`); dostroić
  do realnych nagrań.
- **Format komunikatu zenity** (czytelny wiek: „2 minuty temu" vs „wczoraj"; rozmiar z `du -sh`).
- **Zachowanie `setka-tray` przy braku `StatusNotifierWatcher` przy starcie** — domyślnie polegać
  na późnym dowiązaniu AyatanaAppIndicator3 + drobny `X-GNOME-Autostart-Delay`; dostroić.

### Surfaced (do świadomości operatora — nie blokuje)

- **Niespójność defaultów roota między pakietami**: obsession hardcode `~/Wideo/obs`/`~/Videos/obs`,
  fermata env-default `~/Videos/obs-recordings`. Ten plan przyjmuje `~/Wideo/obs` (realia). Ujednolicenie
  defaultów we wszystkich pakietach jest **poza zakresem** (osobny, drobny follow-up).
- **„Najnowszy" przy odpaleniu między sesjami**: jeśli operator kliknie delete-last zanim nagra
  dzisiejsze ujęcie, najnowszym folderem jest nagranie z wcześniejszej sesji. Mitygacja: zenity
  pokazuje nazwę+wiek+rozmiar, a operacja jest odwracalna (kosz). Wystarczające w tej iteracji.

## High-Level Technical Design

> *Ilustruje zamierzony kształt — wskazówka kierunkowa do recenzji, nie specyfikacja do
> odtworzenia 1:1.*

```
  ┌─────────────┐         ┌──────────────────┐
  │  tray menu  │         │  skrót GNOME     │   (oba: tylko wyzwalacze)
  │ (setka-tray)│         │  (gsettings)     │
  └──────┬──────┘         └────────┬─────────┘
         │  subprocess              │  command=
         └───────────┬──────────────┘
                     ▼
            setka-live  show | delete-last        (jedno źródło prawdy)
                     │
        show ────────┤──────────► live-layout.sh (istnieje)
                     │
   delete-last ──────┘  (czysty bash, bez OBS/serwera)
        1. root = ${SETKA_RECORDINGS_ROOT:-~/Wideo/obs} (fallback ~/Videos/obs)
        2. walidacja roota: niepusty / katalog / != $HOME
        3. najnowszy podkatalog z (metadata.json + plik wideo), wg mtime
           └─ brak → notify-send „brak nagrania", exit
        4. zenity --question (nazwa + wiek + rozmiar);  rc != 0 → cicho exit (fail-safe)
        5. gio trash "<katalog>"   (odwracalne)
        6. notify-send (sukces + „przywróć z Kosza" / błąd)
```

Przepływ jest fail-safe i odwracalny: każdy stan inny niż „prawidłowy katalog + zenity rc 0"
kończy się brakiem akcji i powiadomieniem; nawet udane przeniesienie da się cofnąć z kosza.

## Implementation Units

- [x] **Unit 1: `setka-live delete-last` — przeniesienie ostatniego nagrania do kosza (bash, self-contained)**

**Goal:** Podkomenda `setka-live delete-last`: ustal root nagrań, znajdź najnowszy prawidłowy
katalog nagrania, potwierdź (zenity z nazwą/wiekiem/rozmiarem), przenieś do kosza (`gio trash`),
powiadom (notify-send). Bez OBS, bez serwera.

**Requirements:** R3, R3a, R4, R5, R6

**Dependencies:** Brak.

**Files:**
- Modify: `deploy/live/bin/setka-live` (czyste funkcje + `cmd_delete_last` + `delete-last)` w
  `case` w `main()` + wpis w usage)
- Test: `deploy/live/tests/test_setka_live.sh` (rozszerzyć)
- Modify: `deploy/live/README.md` (dokumentacja podkomendy + zachowanie + env)

**Approach:**
- Indirekcja env (jak `LAYOUT_BIN`): `GIO_BIN` (default `gio`), `ZENITY_BIN` (`zenity`),
  `NOTIFY_BIN` (`notify-send`), `SETKA_RECORDINGS_ROOT`, opcjonalnie `REC_VIDEO_GLOBS`.
- Czyste, testowalne funkcje:
  - `resolve_recordings_root()` → echo zwalidowanego roota lub exit z błędem: jeśli
    `SETKA_RECORDINGS_ROOT` ustawiony, użyj go (`expanduser`); inaczej pierwszy istniejący z
    `~/Wideo/obs`, `~/Videos/obs`. Walidacja: niepusty, absolutny, istnieje, jest katalogiem,
    `!= $HOME` (i `!= /`) — inaczej err i odmowa (**nigdy** fallback do CWD/$HOME).
  - `is_recording_dir <dir>` → 0, jeśli `dir` zawiera `metadata.json` **oraz** co najmniej jeden
    plik wideo (`*.mp4`/`*.mkv`/`*.mov`/`*.flv`); inaczej !=0.
  - `find_latest_recording <root>` → echo ścieżki najnowszego (wg mtime) bezpośredniego
    podkatalogu, dla którego `is_recording_dir` == 0; pusto, gdy brak. Pomija nie-katalogi i
    symlinki (resolve + sprawdź `parent == root`).
  - `describe_recording <dir>` → „nazwa | wiek czytelnie | rozmiar (`du -sh`)".
  - `cmd_delete_last`: root → latest → brak? `notify-send` „Brak nagrania do usunięcia", exit 0.
    Inaczej `zenity --question --default-cancel --icon=dialog-warning` z opisem (R4); rc != 0 →
    cicho exit (fail-safe); rc == 0 → `gio trash "<dir>"`; sukces → `notify-send` „Przeniesiono
    do kosza: <nazwa> (przywrócisz z Kosza w Plikach)"; błąd `gio` → `notify-send --urgency=critical`.
- Best-effort dla narzędzi GUI (brak `zenity`/`notify-send` → `log`/`err` + sensowny fallback),
  ale potwierdzenie jest twardym warunkiem przeniesienia.
- Zachowaj istniejący kontrakt dispatchu: nieznana komenda → exit 2.

**Patterns to follow:** `cmd_show`/`cmd_start` + indirekcja w `setka-live`; `live-layout.sh`
(`"${VAR:-default}"`, `log`/`err`, bramki); walidacja `exists`+`is_dir`+pod-rootem jak w
`recordings.rs`; pojęcie „prawidłowe nagranie" jak w `advanced_scene_switcher_extractor.py`.

**Test scenarios:** (recorder-mock dla `GIO_BIN`/`ZENITY_BIN`/`NOTIFY_BIN`; tmp root z atrapami
nagrań: `mkdir <ts>/`, `touch <ts>/metadata.json`, `touch <ts>/clip.mp4`, kontrola mtime)
- Happy path: root z 3 prawidłowymi katalogami o różnych mtime → `find_latest_recording` zwraca
  najnowszy; zenity-mock rc 0 → `gio trash <najnowszy>` w logu + `notify-send` z nazwą folderu.
- Error path (R4): zenity-mock rc 1 → **brak** `gio trash` w logu; brak destrukcyjnej notyfikacji.
- Edge case: katalog bez prawidłowych nagrań (same pliki / podkatalog bez `metadata.json`) →
  brak zenity, brak `gio trash`, `notify-send` „brak nagrania".
- Edge case (walidacja struktury): podkatalog z `metadata.json` ale bez pliku wideo →
  `is_recording_dir` != 0 → pominięty; podkatalog z wideo bez `metadata.json` → pominięty.
- Edge case (root): `SETKA_RECORDINGS_ROOT` = `""`, względny, nieistniejący, plik, `$HOME`, `/` →
  odmowa (err), **zero** globowania CWD/$HOME, brak `gio trash`.
- Edge case (fallback): brak env, `~/Wideo/obs` nie istnieje, `~/Videos/obs` istnieje → użyty fallback.
- Edge case (symlink-escape): najnowszy „podkatalog" to symlink wskazujący poza root → pominięty.
- Edge case (opis): `describe_recording` zawiera nazwę, wiek i rozmiar (asercja na obecności pól).
- Error path (`gio`): `GIO_BIN` zwraca !=0 → `notify-send` pokazuje **błąd**, nie „przeniesiono".
- Dispatch: `setka-live delete-last` trafia w `cmd_delete_last`; nieznana komenda → exit 2
  (regresja istniejącego dispatchu); żadna komenda nie dotyka `paternologia.service` (jak istniejący test).

**Verification:** rozszerzony `test_setka_live.sh` przechodzi; `gio trash` jest wywoływany
wyłącznie po potwierdzeniu, tylko na prawidłowym katalogu nagrania ściśle pod zwalidowanym rootem;
nieprawidłowy root nigdy nie prowadzi do globowania $HOME/CWD.

---

- [x] **Unit 2: `setka-tray` — ikona tray z menu akcji (PyGObject)**

**Goal:** Lekka apka tray (GTK3 + AyatanaAppIndicator3) z menu wyzwalającym podkomendy `setka-live`.

**Requirements:** R1 (część: tray), R2

**Dependencies:** Unit 1 (menu wywołuje `delete-last`; `show` już istnieje).

**Files:**
- Create: `deploy/live/bin/setka-tray` (python3, shebang `#!/usr/bin/env python3`)
- Create: `deploy/live/autostart/setka-tray.desktop` (szablon do instalacji)
- Test: `deploy/live/tests/test_setka_tray.py` (test czystej części: tabela menu → komendy)

**Approach:**
- `gi.require_version("Gtk","3.0")` + `gi.require_version("AyatanaAppIndicator3","0.1")`;
  `Indicator.new(...)`, `set_status(ACTIVE)`, `set_menu(menu)`.
- Menu: „Pokaż okna" → `["setka-live","show"]`; „Usuń ostatnie nagranie" → `["setka-live","delete-last"]`;
  separator; „Zakończ". Komendy odpalane `subprocess.Popen([...])` (lista argów, bez `shell=True`).
- Wydzielić **czystą strukturę menu** (lista krotek etykieta→argv) jako dane testowalne bez GUI;
  warstwa GTK tylko ją renderuje.
- `.desktop`: `Type=Application`, `Exec=` absolutna ścieżka (uzupełniana przez install.sh),
  `StartupNotify=false`, `OnlyShowIn=GNOME;Unity;`, `X-GNOME-Autostart-enabled=true`,
  drobny `X-GNOME-Autostart-Delay` na wypadek późnego `StatusNotifierWatcher`.
- Plik zaczyna się od dwóch linii `# ABOUTME:`.

**Execution note:** Warstwa GTK/AppIndicator trudna do testów jednostkowych — utrzymać cienką;
logika (mapowanie menu→komenda) testowana osobno.

**Patterns to follow:** brak lokalnego precedensu GUI; trzymać się decyzji z research (GTK3,
Ayatana, menu + `set_status(ACTIVE)`).

**Test scenarios:**
- Happy path: tabela menu zawiera „Pokaż okna"→`["setka-live","show"]` i „Usuń ostatnie
  nagranie"→`["setka-live","delete-last"]` (asercja na czystej strukturze).
- Edge case: „Zakończ" mapuje na czyste wyjście (brak komendy zewnętrznej).
- (GUI/AppIndicator — weryfikacja manualna: ikona pojawia się, menu działa.)

**Verification:** `test_setka_tray.py` przechodzi; manualnie: ikona w tray, „Pokaż okna" układa
okna, „Usuń ostatnie nagranie" uruchamia przepływ z Unitu 1.

---

- [x] **Unit 3: instalacja skrótów GNOME + traya (install.sh + helper)**

**Goal:** Idempotentnie zainstalować `setka-tray`, autostart `.desktop` oraz globalne skróty
GNOME (`Super+Shift+S` show, `Super+Shift+D` delete-last) wskazujące na podkomendy `setka-live`;
defensywne sprawdzenia środowiska.

**Requirements:** R1 (część: skróty + autostart traya)

**Dependencies:** Unit 2.

**Files:**
- Create: `deploy/live/bin/live-keybindings.sh` (czyste funkcje gsettings, env `GSETTINGS_BIN`)
- Modify: `deploy/live/install.sh` (instalacja `setka-tray`, `.desktop` z abs. `Exec`, wywołanie
  helpera skrótów, defensywny check `StatusNotifierWatcher` + zależności)
- Test: `deploy/live/tests/test_keybindings.sh` (recorder-mock `gsettings`)
- Modify: `deploy/live/tests/test_install.sh` (rozszerzyć o tray/.desktop/skróty)
- Modify: `deploy/live/README.md` (sekcja skrótów + traya + tabela domyślnych klawiszy + env
  `SETKA_RECORDINGS_ROOT`)

**Approach:**
- `live-keybindings.sh`: `kb_add path name command keys` — append-if-absent do `custom-keybindings`
  z osobnym case na `@as []`; ścieżki **własne, nazwane** (`.../setka-show/`, `.../setka-delete-last/`)
  zakończone `/`; per-binding `name`/`command`/`binding`. Domyślne klawisze env (`KB_SHOW`=`<Super><Shift>s`,
  `KB_DELETE`=`<Super><Shift>d`).
- `install.sh`: kopiuje `setka-tray` → `~/.local/bin` (0755, `install_file`); instaluje
  `setka-tray.desktop` → `~/.config/autostart` z podstawioną absolutną `Exec`; woła
  `live-keybindings.sh` (pomijalne env-em w testach, jak istniejące efekty uboczne); defensywny
  `gdbus` check `org.kde.StatusNotifierWatcher` + warn o brakujących `gir1.2-*`/`zenity`/
  `notify-send`/`gio`. Może udokumentować/ustawić `SETKA_RECORDINGS_ROOT`, jeśli != default.
- Idempotencja: ponowny install = no-op (backup tylko przy różnicy, skróty bez duplikatów).

**Patterns to follow:** `install.sh` (`install_file`, backup, efekty uboczne tylko dla domyślnego
katalogu), `live-layout.sh` (env indirekcja + czyste funkcje), `test_install.sh`.

**Test scenarios:** (recorder-mock `gsettings`)
- Happy path: pusta lista (`@as []`) → po `kb_add` lista zawiera nową ścieżkę; per-binding
  `name`/`command`/`binding` ustawione (asercja na logu gsettings).
- Edge case (idempotencja): `kb_add` z istniejącą ścieżką → lista bez duplikatu (no-op).
- Edge case: lista z istniejącym customem użytkownika → nowa ścieżka **dopisana**, stara zachowana.
- Happy path install: `setka-tray` skopiowany do BIN_DIR (0755), `.desktop` w autostart z abs. `Exec`.
- Edge case install: ponowny install identycznych plików → brak backupu (no-op).
- Error path: brak `StatusNotifierWatcher` (gdbus-mock) → ostrzeżenie, install nie zawala (exit 0).

**Verification:** `test_keybindings.sh` i rozszerzony `test_install.sh` przechodzą; po realnej
instalacji skróty działają bez restartu sesji, tray startuje przy logowaniu (weryfikacja manualna).

## System-Wide Impact

- **Interaction graph:** Nowa podkomenda `setka-live delete-last` (czysty bash) + tray + skróty
  jako nowe zewnętrzne punkty wejścia. **Brak zmian** w paternologii, OBS WebSocket, MIDI/bridge/kiosk.
- **Error propagation:** Każdy stan != „prawidłowy katalog + zenity rc 0" → brak akcji +
  `notify-send`. Błąd `gio` → notyfikacja krytyczna, nie cisza.
- **State lifecycle / destrukcyjność:** Operacja jest **odwracalna** (kosz). Brak TOCTOU-ryzyka
  wymagającego kontraktu mtime — najgorszy przypadek (zły folder) jest cofalny z kosza. Ochrona:
  walidacja roota (`!= $HOME`, bez fallbacku do CWD), walidacja struktury kandydata, `parent ==
  root` (anty-symlink-escape), zenity `--default-cancel`, fail-safe.
- **API surface parity:** Wszystkie wyzwalacze (tray, skrót) idą przez tę samą `setka-live
  delete-last` → spójne zachowanie i potwierdzenie niezależnie od źródła.
- **Integration coverage:** recorder-mock `gio`/`zenity`/`notify-send` + realny tmp filesystem
  (atrapy nagrań) dowodzą, że `gio trash` leci tylko po potwierdzeniu na prawidłowym katalogu.

## Risks & Dependencies

- **Operacja na całym folderze, ale odwracalna:** mitygacja — `gio trash` (nie `rm`), walidacja
  roota/struktury/pod-rootem, zenity z nazwą+wiekiem+rozmiarem, fail-safe na każdy stan != „ok".
  Świadomie bezpieczniejsze niż istniejące `remove_dir_all` w fermacie.
- **Zależność od kosza GNOME (`gio`/gvfs):** obecne i zweryfikowane; gdyby `gio trash` zawiódł —
  notyfikacja błędu, brak twardego kasowania w zastępstwie (fail-safe, nic nie ginie).
- **Niespójność defaultów roota między pakietami** (obsession/fermata/ten plan) — patrz „Surfaced";
  ujednolicenie poza zakresem.
- **Zależności GNOME (tray):** rozszerzenie appindicator i `gir1.2-*` muszą być obecne — na Ubuntu
  są; install.sh ostrzega defensywnie, nie zawala.
- **Kolizje skrótów GNOME:** install.sh ostrzega, gdy ustawiony `binding` został przejęty.
- **GUI traya nietestowalny jednostkowo:** mitygacja — cienka warstwa GTK, testowalna tabela menu,
  weryfikacja manualna.

## Documentation / Operational Notes

- `deploy/live/README.md`: nowa podkomenda `delete-last` (przenosi ostatnie nagranie do **kosza**,
  odwracalnie; nazwa+wiek+rozmiar w potwierdzeniu; env `SETKA_RECORDINGS_ROOT`), sekcja traya i
  skrótów (domyślne klawisze `Super+Shift+S`/`Super+Shift+D`, jak zmienić, defensywne checki),
  wzmianka o zależnościach GNOME (`gio`/gvfs, appindicator, `gir1.2-*`).
- Reset rigu udokumentowany jako świadomie odłożony (link do origin R7 / przyszła faza).

## Alternative Approaches Considered

- **Logika w paternologii (endpoint HTTP) — poprzednia wersja planu**: odrzucone po doprecyzowaniu.
  Uzasadnienie endpointu (reuse połączenia OBS + `is_recording()` guard) odpadło: root bierzemy z
  env, guard zastąpiła odwracalność. Czysty bash jest prostszy (KISS) i nie wprowadza zależności od
  działającego serwera dla operacji czysto plikowej.
- **Twarde `rm`/`remove_dir_all` (jak fermata)**: odrzucone — nieodwracalne; `gio trash` daje to
  samo UX, ale bezpiecznie.
- **Root z OBS WebSocket `GetRecordDirectory`**: odrzucone — zwraca `RecFilePath` (np. `/home/wojtas`),
  lokalizację surowego pliku przed reorganizacją, nie root sfolderyzowanych nagrań.
- **Root w pliku-configu (YAML)**: odrzucone — żaden konsument roota nie używa pliku; env to ustalona
  konwencja (`FERMATA_RECORDINGS_PATH`, `PATERNOLOGIA_DATA_DIR`) i jest trywialnie testowalny.
- **Tray przez `yad --notification` / `AppIndicator3` (Canonical) / `alltray` / `kdocker`**:
  odrzucone — wymaga apt lub oparte na martwym XEmbed; jedyny działający namespace to AyatanaAppIndicator3.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md](docs/brainstorms/2026-06-04-live-operator-quick-actions-requirements.md)
- Related plans: `docs/plans/2026-06-03-001-feat-setka-live-window-layout-plan.md`,
  `docs/plans/2026-06-02-002-feat-live-session-launcher-plan.md`
- Related code: `deploy/live/bin/setka-live`, `deploy/live/bin/live-layout.sh`,
  `deploy/live/install.sh`,
  `packages/obsession/src/obsession/obs_integration/advanced_scene_switcher_extractor.py`,
  `packages/fermata/src-tauri/src/commands/recordings.rs`
- External (zweryfikowane na maszynie): OBS 32.1.2 profil `live` (hybrid_mp4, RecFilePath=$HOME);
  `gio trash`/gvfs; PyGObject + AyatanaAppIndicator3 (GTK3); `org.gnome.settings-daemon.plugins.media-keys`
  custom-keybindings; zenity 4.0.1; notify-send 0.8.3.
