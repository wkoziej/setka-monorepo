# Warstwa live — orkiestracja OBS + Bitwig + kiosk paternologii

Jedna komenda stawia gotowe środowisko do nagrywania live, jedna robi całościowy restart.
Wszystko jako `systemd --user` (logi w `journalctl --user`), w **trybie na żądanie** — nic
nie wstaje przy logowaniu, dopóki nie odpalisz `setka-live start`.

`paternologia.service` (most MIDI, watchdog) działa **osobno** i nie jest restartowany przez
tę warstwę — target tylko od niej *zależy* (ordering + preflight).

## Instalacja

```bash
deploy/live/install.sh
```

Instalator (idempotentny, backupuje różniące się pliki):
- kopiuje unity → `~/.config/systemd/user/`,
- kopiuje skrypty → `~/.local/bin/` (`setka-live`, `live-preflight.sh`, `paternologia-kiosk.sh`,
  `live-layout.sh`),
- robi `systemctl --user daemon-reload`,
- **wycofuje stary kiosk-autostart** `~/.config/autostart/paternologia-kiosk.desktop`
  (zmienia nazwę na `.disabled-<stamp>` — odwracalne; kiosk przechodzi pod systemd).

Upewnij się, że `~/.local/bin` jest w `PATH` (instalator ostrzeże, jeśli nie).

Do `setka-live show` (układanie okien) potrzebny jest `wmctrl` — instalator tylko ostrzega, gdy
go brak (nie blokuje instalacji): `sudo apt install wmctrl`.

## Komendy operatorskie

```bash
setka-live start        # postaw komplet (OBS + Bitwig + kiosk) po preflighcie; na końcu układa okna
setka-live stop         # zatrzymaj całą warstwę GUI
setka-live restart      # całościowy restart GUI (stop+start; re-weryfikuje preflight)
setka-live status       # stan członków + paternologia /health + środowisko graficzne
setka-live show         # wyciągnij na wierzch i ułóż okna na dwóch monitorach (patrz niżej)
setka-live delete-last  # przenieś ostatnie nagranie do kosza z potwierdzeniem (patrz niżej)
setka-live new-take     # otwórz czysty projekt Bitwig z szablonu (świeży stan do nagrywania)
```

### `setka-live delete-last` — przeniesienie ostatniego nagrania do kosza

Przenosi **cały katalog** najnowszego nagrania do kosza GNOME (`gio trash`) — operacja **odwracalna**
(przywrócisz z Kosza w Menedżerze Plików / Nautilusa).

Przepływ:

1. Ustala root nagrań z `SETKA_RECORDINGS_ROOT` (lub fallback `~/Wideo/obs` → `~/Videos/obs`).
2. Znajduje najnowszy (wg mtime) podkatalog roota zawierający `metadata.json` + plik wideo.
3. Pyta przez `zenity` o potwierdzenie — pokazuje nazwę, wiek i rozmiar katalogu.
4. Po potwierdzeniu przenosi do kosza przez `gio trash`; informuje przez `notify-send`.
5. Anulowanie lub zamknięcie okna → brak akcji (fail-safe).

Zmienne środowiskowe:

| Zmienna | Domyślna wartość | Opis |
|---------|-----------------|------|
| `SETKA_RECORDINGS_ROOT` | `~/Wideo/obs` (fallback `~/Videos/obs`) | Root katalogu nagrań |
| `REC_VIDEO_GLOBS` | `*.mp4 *.mkv *.mov *.flv` | Rozszerzenia plików wideo |

Walidacja roota: musi być niepustą, **absolutną** ścieżką do istniejącego katalogu, różną od
`$HOME` i `/`. Zmienna ustawiona na pusty string lub ścieżkę względną → odmowa z komunikatem błędu.

Wymagane narzędzia: `zenity` (potwierdzenie — bez niego operacja jest blokowana), `gio` (kosz),
`notify-send` (powiadomienia, best-effort).

### `setka-live new-take` — czysty projekt Bitwig z szablonu

Otwiera w Bitwigu **nienazwany projekt z szablonu** — świeży stan po skasowaniu nieudanego ujęcia.

Mechanizm: `flatpak run <app-id> <szablon>`. Działający Bitwig przejmuje plik
(*„Bitwig Studio is already running — opening files"*) i tworzy nowy projekt z szablonu **bez
ubijania instancji**. Gdy Bitwig nie działa, flatpak wystartuje go z tym szablonem.

Zmienne środowiskowe:

| Zmienna | Domyślna wartość | Opis |
|---------|-----------------|------|
| `BITWIG_TEMPLATE` | `~/Bitwig Studio/Library/Templates/template.bwtemplate` | Szablon projektu (ten sam, którym startuje `bitwig.service`) |
| `BITWIG_APP_ID` | `com.bitwig.BitwigStudio` | Id aplikacji flatpak |

Uwagi:
- Brak szablonu → odmowa z komunikatem błędu (FAIL FAST), bez wołania flatpaka.
- **Niezapisane zmiany** w bieżącym projekcie wywołują własny prompt zapisu Bitwiga (ochrona przed
  utratą danych — nie da się go bezpiecznie wyciszyć).
- To wyłącznie **połowa-Bitwig** „resetu rigu" — **nie** czyści Model:Samples / MicroFreak / RC-600.
  Pełny reset sprzętu pozostaje osobną, większą fazą (API rozszerzeń Bitwiga nie zarządza projektami,
  dlatego sięgamy po CLI-open pliku).

### `setka-live show` — układanie okien

Wyciąga na wierzch i układa komplet okien w stałym układzie na dwóch monitorach:

| Monitor | Okno |
|---------|------|
| **lewy** (najmniejszy offset X) | Bitwig — cała powierzchnia |
| **prawy**, górna połowa | OBS |
| **prawy**, dolna połowa | Paternologia (kiosk) |

`setka-live start` wykonuje to samo układanie na końcu (best-effort — błąd układania nie wywraca
startu). `show` można odpalić ręcznie, kiedy okna się rozjadą. Komenda jest idempotentna.

Pułapki:
- **Tylko X11.** Układanie idzie przez `wmctrl` (EWMH na GNOME/Xorg). Na Wayland komenda jawnie
  odmawia zamiast cicho zawieść.
- **WM_CLASS OBS/Bitwiga** są konfigurowalne na górze `live-layout.sh` (`OBS_CLASS`,
  `BITWIG_CLASS`); kiosk ma własny `--class=setka-kiosk`. Potwierdzone realnie na tej maszynie:
  OBS = `obs.obs`, Bitwig (flatpak) = `com.bitwig.BitwigStudio`. Gdyby się zmieniły, sprawdź
  `wmctrl -lx` przy żywych oknach i nadpisz przez env. Brak dopasowanego okna → pominięte +
  raport (nie błąd).
- **Kiosk musi wstać przez `paternologia-kiosk.sh`** (np. `setka-live start`/`restart`), żeby miał
  klasę `setka-kiosk`. Kiosk celowo używa **nie-snapowego `google-chrome`** (`/opt/google/chrome`):
  snap Brave dwoił raportowaną pozycję okna i odłączał się od `kiosk.service` (`Type=exec` → usługa
  natychmiast `inactive`, okno osierocone). Świeży profil chrome wymaga `--no-first-run`
  `--no-default-browser-check`, inaczej zamiast `/live` pokazuje ekran powitalny.
- **`wmctrl -lG` MYLNIE raportuje geometrię okien Chromium** — pokazuje pozycję ~2× rzeczywistej.
  Samo ustawianie (`wmctrl -e`) działa poprawnie; weryfikuj WZROKOWO, nie po `wmctrl -lG`. Kiosk
  faktycznie ląduje w dolnej połowie prawego monitora, mimo że `-lG` zawyża współrzędne.
- **Geometria** liczona na żywo z `xrandr --listmonitors` (offsety, nie zaszyte nazwy), więc
  przeżywa zamianę kabli/nazw monitorów.
- **OBS nie zwęża się poniżej swojego minimum** (zadokowane panele wymuszają min-rozmiar; bez ich
  schowania nie zmniejszysz okna nawet myszą), więc górna połowa prawego monitora może być przez
  OBS nadpisana większym oknem. To ograniczenie OBS, nie błąd układania — okno i tak jest wyciągane
  na wierzch i widoczne.

## Mapa unitów

| Unit | Rola |
|------|------|
| `live-recording.target` | spina członków (tryb na żądanie, bez `WantedBy=default.target`) |
| `live-preflight.service` | oneshot gate: virmidi + PipeWire 44100 + karty audio rigu w PipeWire (`REQUIRED_AUDIO_CARDS`) + paternologia `/health` |
| `obs.service` | OBS Studio (`/usr/bin/obs`), `Restart=no` |
| `bitwig.service` | Bitwig (flatpak), `ExecStop=flatpak kill`, `Restart=no` |
| `kiosk.service` | `/live` w `google-chrome --kiosk` (nie-snap, osobny `--user-data-dir`), `Restart=no` |

Kolejność: `paternologia.service` → `live-preflight.service` → {`obs`, `bitwig`, `kiosk`}
(trójka startuje równolegle — OBS i Bitwig są rozdzielne urządzeniowo, nie współdzielą `/dev`).

## Pułapki (czytaj przed grzebaniem)

- **Restart targetu nie restartuje członków.** `systemctl --user restart live-recording.target`
  restartuje tylko pusty target — `Wants/Requires` to zależności *startu*, nie propagacja
  *restartu* (systemd #13841/#24068/#32382). Dlatego `setka-live restart` robi `stop`+`start`,
  a członkowie mają `PartOf=live-recording.target`. **Nie „upraszczaj" tego do `restart`.**
- **Nigdy nie restartuj PipeWire pod żywym Bitwigiem** — wyrywa graf, wiesza silnik audio.
  `setka-live` celowo nigdy nie tyka PipeWire. Jak audio się rozjedzie → ręczny
  „Restart Audio Engine" w Bitwigu.
- **Logi flatpaka w journalu** bywają nieskojarzone z `bitwig.service` (main PID = `bwrap`) —
  przy debugowaniu Bitwiga sprawdzaj też `flatpak ps` i wyjście samego flatpaka.
- **Środowisko graficzne (X11)**: usługi GUI mają `ConditionEnvironment=DISPLAY`. Na tej
  maszynie `DISPLAY=:1` jest w activation env systemd usera. Po ewentualnym przejściu na
  Wayland trzeba przełączyć warunek na `WAYLAND_DISPLAY`. `setka-live status` to raportuje.

## Recovery zawieszonego Bitwiga

Gdy silnik audio Bitwiga zawiśnie (np. po replug/utracie urządzenia):

```bash
pkill -9 -f BitwigAudioEngine     # ubij sam silnik audio
# następnie w UI Bitwiga: Settings → Audio → Restart Audio Engine (ręcznie, nieautomatyzowalne)
```

Jeśli to nie pomoże, pełny restart warstwy GUI: `setka-live restart` (most MIDI zostaje żywy).
Rzadki restart samego mostu MIDI (poza zakresem `setka-live`):

```bash
systemctl --user restart paternologia.service
```

## Ikona tray i autostart

`setka-tray` (zainstalowany przez `install.sh`) to lekka apka systemu tray — ikona z menu
szybkich akcji operatorskich. Startuje automatycznie przy logowaniu do sesji GNOME (przez
`~/.config/autostart/setka-tray.desktop`).

Menu traya:
- **Pokaż okna** → wywołuje `setka-live show`
- **Nowy projekt Bitwig** → wywołuje `setka-live new-take`
- **Usuń ostatnie nagranie** → wywołuje `setka-live delete-last`
- **Zakończ** → zamyka samą apkę tray

Wymagania traya (instalator ostrzega, gdy brakuje):
- Rozszerzenie GNOME: `gnome-shell-extension-appindicator` (StatusNotifierWatcher) — na Ubuntu
  24.04 zazwyczaj preinstalowane.
- Pakiety apt: `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1`.

Jeśli ikona nie pojawia się po zalogowaniu: sprawdź rozszerzenie w _GNOME Tweaks → Rozszerzenia_
lub uruchom `setka-tray` ręcznie z terminala i sprawdź błędy.

## Globalne skróty klawiaturowe GNOME

Instalowane przez `install.sh` (idempotentnie; działają bez restartu sesji):

| Skrót | Akcja |
|-------|-------|
| `Super+Shift+S` | `setka-live show` (pokaż/ułóż okna) |
| `Super+Shift+D` | `setka-live delete-last` (usuń ostatnie nagranie) |
| `Super+Shift+N` | `setka-live new-take` (czysty projekt Bitwig z szablonu) |

Skróty wpisywane są do `org.gnome.settings-daemon.plugins.media-keys.custom-keybindings`
i nie nadpisują skrótów użytkownika — nowe ścieżki są tylko dołączane (append-if-absent).

Aby zmienić domyślne klawisze — ustaw env przed `install.sh`:

```bash
KB_SHOW='<Super><Shift>F1' KB_DELETE='<Super><Shift>F2' KB_NEW_TAKE='<Super><Shift>F3' deploy/live/install.sh
```

Zmiana działa bez restartu sesji GNOME — skróty są aktywne od razu po instalacji.

## Testy

```bash
deploy/live/tests/test_install.sh
deploy/live/tests/test_keybindings.sh
deploy/live/tests/test_live_preflight.sh
deploy/live/tests/test_setka_live.sh
deploy/live/tests/test_live_layout.sh
deploy/live/tests/test_kiosk_class.sh
```

Plain shell (`bats` nie jest wymagany). Logikę warunków/dyspozytora testujemy na realnych
kształtach danych i przez indirekcję komend — bez mutowania żywego systemd ani gsettings.
