# Stabilność USB rigu live

## Problem

Drzewo USB rigu re-enumeruje się samoistnie (sprzęt znika i wraca z nowym „device
number"). Każdy taki flap:

- **zrywa audio** — WirePlumber gubi kartę (RC-600/Notepad znikają z PipeWire/Bitwiga),
- **zrywał MIDI** — most PACER tracił subskrypcję ALSA (to już samo-naprawialne, patrz
  `packages/paternologia` + TODO sekcja 5).

Diagnoza (2026-06-03): 15 re-enumeracji w ciągu dnia, **bez** twardych błędów USB
(`-71`/`-110`/over-current) → to **nie** brownout ani zły kabel. Huby stały na
`power/control=auto` (globalny `autosuspend=2s`); o 21:56 re-enumerował się sam hub
`0424:2422`, ciągnąc za sobą RC-600. Wskazuje to na runtime-PM (autosuspend) i/lub
fizyczne dotykanie sprzętu w trakcie setupu.

## Fix — wyłączenie autosuspend (warstwa 1, najtańsza, odwracalna)

### Wariant A (zalecany dla dedykowanej maszyny rigu): globalnie, kernel param

Najpewniejszy — obejmuje też generyczne huby pośrednie (`1-2`, `1-2.4`, `1-2.4.4`),
których VID-ów nie targetujemy. Dla desktopu rigu pobór prądu bezczynnego USB jest bez
znaczenia.

```bash
# /etc/default/grub → dopisz do GRUB_CMDLINE_LINUX_DEFAULT:  usbcore.autosuspend=-1
sudo update-grub && reboot
# weryfikacja po reboocie:
cat /sys/module/usbcore/parameters/autosuspend   # → -1
```

### Wariant B: reguła udev tylko dla VID-ów rigu (chirurgiczne)

Nie rusza reszty USB. Nie obejmie generycznych hubów pośrednich — jeśli flapy zostaną,
przejdź na wariant A.

```bash
sudo deploy/usb/install.sh
```

### Test na żywo przed instalacją (bez reboota, bez reguł)

```bash
# wymusza 'on' na hubie RC-600 i hubach kontrolera 1; obserwuj czy flapy ustają
for d in 3-4 usb3 1-2 1-2.4 1-2.4.4; do echo on | sudo tee /sys/bus/usb/devices/$d/power/control; done
```

## Warstwa 2 — fizyka (jeśli flapy zostają mimo wyłączonego autosuspend)

Brak błędów -71/-110 czyni to mniej prawdopodobnym, ale:

- Podłącz RC-600/Notepad/PACER do **zasilanego** huba, możliwie bezpośrednio do płyty.
- Skróć łańcuch hubów — **Notepad wisi 4 poziomy głęboko** (`1-2 → 1-2.4 → 1-2.4.4 →
  1-2.4.4.2`), co jest kruche.

## Warstwa 3 — odzysk WirePlumbera po flapie

Świeży WirePlumber wykrywa wszystkie karty bez problemu — gubi je tylko, gdy **przegapi
pojedyncze zdarzenie hotplug `add`**. Ręczny odzysk (nie rusza pipewire, klienci wracają):

```bash
systemctl --user restart wireplumber
```

**Uwaga:** automatyczny restart WirePlumbera na każdy `add` karty jest **odradzany** — restart
mrugałby audio Bitwiga w środku setu (gorszy niż choroba). Najpierw eliminujemy flapy
(warstwa 1/2); odzysk audio zostaje świadomą akcją operatora.
