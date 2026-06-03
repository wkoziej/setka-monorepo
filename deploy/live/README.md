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
setka-live start     # postaw komplet (OBS + Bitwig + kiosk) po preflighcie; na końcu układa okna
setka-live stop      # zatrzymaj całą warstwę GUI
setka-live restart   # całościowy restart GUI (stop+start; re-weryfikuje preflight)
setka-live status    # stan członków + paternologia /health + środowisko graficzne
setka-live show      # wyciągnij na wierzch i ułóż okna na dwóch monitorach (patrz niżej)
```

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
  klasę `setka-kiosk`. Zwykła Brave to `brave.Brave` — kiosk uruchomiony „ręcznie" nie zostanie
  rozpoznany (i celowo nie zderza się z prywatną Brave operatora).
- **Geometria** liczona na żywo z `xrandr --listmonitors` (offsety, nie zaszyte nazwy), więc
  przeżywa zamianę kabli/nazw monitorów.
- **OBS nie trafia pixel-perfect w połowę monitora.** Zweryfikowane na żywo: Bitwig ląduje 1:1,
  ale OBS ma `gravity: Static`, ramkę ~37 px i wymuszony minimalny rozmiar przez zadokowane
  panele (bez ich schowania nie zmniejszysz okna nawet myszą) — więc ląduje w prawym górnym
  obszarze z offsetem, nie idealnie w połowie. To ograniczenie OBS/Muttera, nie błąd układania;
  okno i tak jest wyciągnięte na wierzch i widoczne. Ewentualna korekta `_NET_FRAME_EXTENTS`
  w `layout_place` sama tego nie zlikwiduje (offset jest większy niż ramka).

## Mapa unitów

| Unit | Rola |
|------|------|
| `live-recording.target` | spina członków (tryb na żądanie, bez `WantedBy=default.target`) |
| `live-preflight.service` | oneshot gate: virmidi + PipeWire 44100 + paternologia `/health` |
| `obs.service` | OBS Studio (`/usr/bin/obs`), `Restart=no` |
| `bitwig.service` | Bitwig (flatpak), `ExecStop=flatpak kill`, `Restart=no` |
| `kiosk.service` | `/live` w `brave --kiosk` (osobny `--user-data-dir`), `Restart=no` |

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

## Testy

```bash
deploy/live/tests/test_install.sh
deploy/live/tests/test_live_preflight.sh
deploy/live/tests/test_setka_live.sh
deploy/live/tests/test_live_layout.sh
deploy/live/tests/test_kiosk_class.sh
```

Plain shell (`bats` nie jest wymagany). Logikę warunków/dyspozytora testujemy na realnych
kształtach danych i przez indirekcję komend — bez mutowania żywego systemd.
