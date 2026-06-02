---
title: "Bitwig pada w trakcie nagrania na Linux: resampling 44.1↔48k PipeWire + kontencja USB"
date: 2026-06-01
tags: [audio, pipewire, bitwig, usb, rc-600, obs, linux, sample-rate, latency, recording]
component: audio-capture
status: resolved
related_plans:
  - docs/plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md
---

# Bitwig pada w trakcie nagrania: sample-rate + kontencja USB

## Symptom

- Podczas równoczesnego nagrywania w **Bitwigu** (multitrack z RC-600) i **OBS** Bitwig **nagle przestaje nagrywać** / silnik audio wisi.
- OBS przestaje widzieć część kamer (czerń na źródłach).
- Po restarcie PipeWire pod działającym Bitwigiem: Bitwig **nie widzi RC-600** i **nie da się go zamknąć** (UI zamrożone).

## Środowisko

- Płyta **MSI B550-A PRO (MS-7C56)**, Ryzen + B550, **Ubuntu + PipeWire**.
- **RC-600** = jedyny interfejs audio DAW, 8 ch USB, natywnie **44100 Hz**, do Bitwiga.
- OBS: audio z Notepada 12FX + 4 kamery USB (StarLeaf, Creative VF0700, 2× Logitech C270).
- Bitwig (Flatpak) chodzi **przez PipeWire**, nie po ALSA na wyłączność (potwierdzone: `pw-link` pokazuje `Bitwig Studio:inXX ← alsa_input...RC-600`; w `/proc/<pid>/fd` brak `/dev/snd` audio, tylko MIDI).

## Przyczyny (dwie, niezależne)

1. **Wymuszony resampling sample-rate (główna).** RC-600 jest hardware'owo taktowany na **44100**, a PipeWire miał graf zablokowany na `clock.allowed-rates = [ 48000 ]`. PipeWire **resamplował** strumień RC-600 44.1↔48k w obie strony — adaptacyjny resampling taktowanego sprzętowo wejścia DAW pod obciążeniem powoduje dropouty i zatrzymanie silnika.
2. **Kontencja pasma USB 2.0.** Wszystkie interfejsy (RC-600, Notepad, kamery) to urządzenia **USB 2.0 (480 Mbit)**. Cztery kamery + audio na jednym kontrolerze (Bus 001) przekraczają pasmo izochroniczne → kamery/strumienie się nie mieszczą.

### Topologia kontrolerów (kluczowe)

Płyta ma **dwa kontrolery xHCI**:

| PCI | Co | Magistrale |
|---|---|---|
| `2d:00.3` Matisse (CPU) | bezpośrednie linie procesora | Bus 003 (480M) + Bus 004 (10G) |
| `02:00.0` B550 chipset | przez link do CPU | Bus 001 (480M) + Bus 002 (10G) |

**Urządzenie USB 2.0 zawsze enumeruje się na magistrali 480M (Bus 001 lub Bus 003), nigdy na pustych 10 Gbit (Bus 002/004)** — te niosą tylko SuperSpeed. Czyli nie da się „odciążyć" kamer/audio na puste szybkie kontrolery; jedyna gra to rozdział między Bus 001 i Bus 003.

## Rozwiązanie

1. **PipeWire: pozwól na 44.1** — drop-in `~/.config/pipewire/pipewire.conf.d/10-rc600-44100.conf`:
   ```
   context.properties = {
       default.clock.rate          = 44100
       default.clock.allowed-rates = [ 44100 48000 ]
   }
   ```
   `systemctl --user restart pipewire pipewire-pulse wireplumber`. Graf podąża za natywnym 44.1 RC-600 (zero resamplingu na ścieżce DAW), do treści 48k wraca, gdy bezczynny.
   > ⚠ Uwaga na heredoc w terminalu: wklejony `<<'EOF'` z wcięciami **nie zamknie** dokumentu (closing `EOF` musi być w kol. 0). Pewniej napisać plik wprost.
2. **RC-600 na kontroler CPU** (rear 10 Gbps Type-A/Type-C grupa „10" na B550-A PRO → Bus 003), z dala od strumieni wideo.
3. **Kamery w OBS → MJPEG** (Input Format), nie YUYV/raw. MJPEG tnie pasmo ~10× → kilka kamer + audio mieści się na jednym kontrolerze niezależnie od portów. To usuwa całe napięcie pasma.

## Reguły operacyjne (na przyszłość)

- **NIE restartuj PipeWire pod działającym Bitwigiem** — wyrywa graf, silnik audio wisi. Najpierw wycisz/zamknij Bitwig.
- **Po przepięciu RC-600 lub restarcie PipeWire → w Bitwigu „Restart Audio Engine"** i ponowny wybór urządzenia w Settings → Audio.
- **Zawieszone UI Bitwiga ratuje ubicie samego procesu** `BitwigAudioEngine-X64-AVX2` (`pkill -9 -f BitwigAudioEngine`) — projekt w UI zostaje; nie trzeba ubijać całej aplikacji.
- **`/dev/videoN` nie są stabilne** po przepięciu USB — w OBS wybieraj kamerę **po nazwie** (lub rozważ `/dev/v4l/by-id/...`). Dwa identyczne C270 to pułapka nazw — różnią się węzłem.

## Weryfikacja

```bash
pw-metadata -n settings | grep -iE "clock.rate|allowed-rates"   # 44100 + [ 44100, 48000 ]
pactl list short sources | grep -i rc-600                       # RUNNING 44100 gdy Bitwig gra
pw-top                                                          # wiersz RC-600: RATE 44100, ERR 0
```

Potwierdzone działającym nagraniem 2026-06-01: po zmianie na 44.1 + rozdziale USB Bitwig nagrywa bez przerwań.

## Powiązania

- Wpływa na **R2** (jedno-przyciskowy record jest bezwartościowy, jeśli Bitwig pada) i **R6** (niezawodność live) w planie orkiestracji.
- [Plan 001 — orkiestracja OBS + Bitwig + paternologia](../plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md)
