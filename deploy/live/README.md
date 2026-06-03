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
- kopiuje skrypty → `~/.local/bin/` (`setka-live`, `live-preflight.sh`, `paternologia-kiosk.sh`),
- robi `systemctl --user daemon-reload`,
- **wycofuje stary kiosk-autostart** `~/.config/autostart/paternologia-kiosk.desktop`
  (zmienia nazwę na `.disabled-<stamp>` — odwracalne; kiosk przechodzi pod systemd).

Upewnij się, że `~/.local/bin` jest w `PATH` (instalator ostrzeże, jeśli nie).

## Komendy operatorskie

```bash
setka-live start     # postaw komplet (OBS + Bitwig + kiosk) po preflighcie
setka-live stop      # zatrzymaj całą warstwę GUI
setka-live restart   # całościowy restart GUI (stop+start; re-weryfikuje preflight)
setka-live status    # stan członków + paternologia /health + środowisko graficzne
```

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
```

Plain shell (`bats` nie jest wymagany). Logikę warunków/dyspozytora testujemy na realnych
kształtach danych i przez indirekcję komend — bez mutowania żywego systemd.
