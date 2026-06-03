---
date: 2026-06-03
topic: setka-live-window-layout
---

# setka-live: wyciągnięcie i ułożenie okien na dwóch monitorach

## Problem Frame
Po `setka-live start` środowisko nagraniowe (OBS + Bitwig + kiosk Paternologii) działa,
ale okna lądują w przypadkowych miejscach / pod innymi oknami. Operator (Wojtas) musi
ręcznie alt-tabować i przeciągać je na właściwe monitory, zanim zacznie nagrywać — co
psuje obietnicę „jednego polecenia". Potrzebna jedna komenda, która wyciąga komplet okien
na wierzch i układa je w stałym, znanym układzie na dwóch monitorach.

## Requirements
- R1. Nowa komenda `setka-live show` wyciąga na wierzch (raise + activate) i układa
  okna OBS, Bitwiga i kiosku Paternologii w stałym układzie na dwóch monitorach.
- R2. Układ docelowy (wybrany):
  - **Lewy monitor (DVI-D-0, 1280×1024):** Bitwig — cała powierzchnia.
  - **Prawy monitor (HDMI-0, 1440×900):** OBS górna połowa, Paternologia (kiosk) dolna połowa.
- R3. `setka-live start` na końcu automatycznie wykonuje ten sam układ, gdy okna już się
  pojawiły. Układanie jest też dostępne osobno przez `setka-live show` (gdy okna się rozjadą).
- R4. Komenda działa idempotentnie — wielokrotne wywołanie zawsze daje ten sam układ.
- R5. Brak któregoś okna (np. Bitwig jeszcze nie wstał) nie wywraca komendy: układa to,
  co istnieje, i czytelnie raportuje, czego zabrakło (FAIL FAST tylko dla realnych błędów,
  nie dla pojedynczego brakującego okna).

## Success Criteria
- Po `setka-live start` (lub `setka-live show`) okna są dokładnie w układzie z R2 bez
  ręcznego dotykania myszą.
- Powtórne `setka-live show` po rozjechaniu okien przywraca układ.
- Gdy jedno z okien nie istnieje, komenda układa pozostałe i wypisuje, którego brakło.

## Scope Boundaries
- Nie obsługujemy Waylanda. Maszyna to GNOME na Xorg (potwierdzone: `XDG_SESSION_TYPE=x11`,
  realny proces Xorg, brak Xwaylanda). Gdyby sesja kiedyś przeszła na Wayland, komenda ma
  jasno odmówić, nie udawać że działa.
- Nie konfigurujemy dynamicznie liczby/rozdzielczości monitorów ani profili `xrandr`.
  Układ celuje w obecny zestaw 2 monitorów; geometria liczona z `xrandr`, nie zaszyta na sztywno.
- Nie ruszamy paternologia.service ani warstwy audio — to czysto okienkowa nakładka.
- Brak GUI/konfiguratora układów; jeden zaszyty układ (R2) wystarcza.

## Key Decisions
- **Narzędzie: `wmctrl` (EWMH), nie GNOME Shell Eval.** Mutter na Xorg w pełni wspiera
  EWMH (move/resize/raise/activate). `gnome-shell Eval` jest zablokowany ze względów
  bezpieczeństwa (zwraca `false`) — celowo nie idziemy tą drogą. `wmctrl`/`xdotool` nie są
  jeszcze zainstalowane → instalator warstwy live musi to dociągnąć / sprawdzić.
- **Komenda nazywa się `show`** (obok start/stop/restart/status) — najkrótsze „pokaż wszystko".
- **Auto po `start` + osobna komenda** — start kończy układaniem, ale `show` można odpalić
  ręcznie kiedykolwiek (okna dryfują, alt-tab, etc.).
- **Geometria z `xrandr`, nie zaszyta** — offsety/rozmiary monitorów czytane na żywo
  (lewy = offset X 0, prawy = offset X = szerokość lewego), żeby przetrwać zmianę kolejności.

## Dependencies / Assumptions
- `wmctrl` (lub `xdotool`) zainstalowane na maszynie live — do dołożenia w `deploy/live/install.sh`
  albo jako preflight-check w `setka-live show`.
- Okna mają stabilne, rozróżnialne `WM_CLASS`. OBS i Bitwig (flatpak) — do potwierdzenia w
  implementacji. Kiosk Paternologii (Brave `--kiosk`) — rozważyć `brave --class=setka-kiosk`,
  by mieć pewny, unikalny uchwyt zamiast zderzać się ze zwykłym Brave.

## Outstanding Questions

### Resolve Before Planning
- (brak — kierunek produktowy domknięty)

### Deferred to Planning
- [Affects R1][Technical] Dokładne `WM_CLASS` dla OBS, Bitwiga-flatpak i kiosku — zweryfikować
  `wmctrl -lx` przy działających oknach; zdecydować czy nadać kioskowi własny `--class`.
- [Affects R3][Technical] Timing auto-układania po `start`: okna pojawiają się z opóźnieniem
  (flatpak Bitwig, kiosk czeka na /health paternologii). Potrzebny krótki polling „czekaj aż
  okno istnieje" z grace-timeoutem, zanim ustawimy geometrię — analogicznie do bram preflightu.
- [Affects R2][Technical] Korekta dekoracji/paneli (pasek GNOME, ramki okien) przy liczeniu
  geometrii — czy `wmctrl -e` z `0,x,y,w,h` trafia 1:1, czy trzeba kompensować `_NET_FRAME_EXTENTS`.
- [Affects R5][Technical] Sposób testowania (warstwa live jest testowana w bashu, narzędzia
  okienkowe trudno mockować) — wydzielić czyste funkcje liczące geometrię z `xrandr` i testować je,
  a wywołania `wmctrl` przez indirekcję `WMCTRL_BIN` (jak `SYSTEMCTL_BIN`/`SYSTEMD_USER_DIR`).

## Next Steps
→ `/ce:plan` — kierunek produktowy domknięty, zostały same decyzje techniczne (mapowanie
  WM_CLASS, timing, geometria, testowalność), które należą do planowania.
