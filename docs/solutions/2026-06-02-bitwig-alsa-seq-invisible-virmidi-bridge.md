---
title: "Bitwig nie widzi wirtualnych portów ALSA seq — most przez snd-virmidi"
date: 2026-06-02
tags: [midi, alsa, seq, rawmidi, virmidi, bitwig, pacer, rtmidi, paternologia, linux]
component: midi-bridge
status: resolved
related_plans:
  - docs/plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md
---

# Bitwig nie widzi portów ALSA seq — fallback snd-virmidi

## Symptom

Model A: paternologia jest jedynym czytelnikiem PACER i robi fan-out na wirtualny
port (`python-rtmidi open_virtual_port("setka-bridge")`). Bitwig miał słuchać mostu.
W praktyce:
- Bitwig pokazywał `MIDI Input Error — PACER MIDI1: Device or resource busy` (próbował
  otworzyć surowy PACER, który trzyma paternologia).
- Po wskazaniu mostu: **`setka-bridge` w ogóle nie pojawiał się** na liście wejść Bitwiga.

## Przyczyna (rdzeń)

**Bitwig na Linuksie enumeruje porty rawmidi (sprzętowe karty `hw:`), a nie wirtualne
porty ALSA *sequencer* tworzone przez inne aplikacje.** `open_virtual_port` daje czysty
port seq bez backingu kartą → dla Bitwiga niewidzialny. To nie jest problem sandboxa
Flatpaka (`devices=all` jest nadane i wystarcza) — to backend MIDI Bitwiga.

Stąd dwa objawy z jednej przyczyny: Bitwig widzi tylko sprzęt → próbuje surowego PACER
(EBUSY) i nie widzi mostu seq.

## Rozwiązanie — snd-virmidi

`snd-virmidi` tworzy wirtualne karty **rawmidi** (`hw:Virmidi`, widoczne jako „Virtual
Raw MIDI" w Bitwigu), zapętlone z portami seq. paternologia pisze do portu seq virmidi,
a Bitwig czyta sprzętową stronę rawmidi.

1. **Załaduj moduł** (utrwal na stałe — patrz niżej):
   ```bash
   sudo modprobe snd-virmidi midi_devs=2
   ```
2. **Most pisze wprost do virmidi.** `MidiBridge.open()` szuka pierwszego portu
   wyjściowego po nazwie `VirMIDI` i otwiera go (`open_port`), z fallbackiem do
   `open_virtual_port` gdy virmidi nie ma. Zero `aconnect`, zero dodatkowych punktów awarii.
3. **Bitwig:** Settings → Controllers → Generic MIDI, **MIDI Input = „Virtual Raw MIDI 1"**
   (pierwszy port virmidi, ten sam, który otwiera most). **Wyłącz surowe `PACER MIDI1/2`**
   jako wejścia — to usuwa EBUSY.

### Utrwalenie modułu (przeżywa reboot)

```bash
echo snd-virmidi | sudo tee /etc/modules-load.d/snd-virmidi.conf
echo "options snd-virmidi midi_devs=2" | sudo tee /etc/modprobe.d/snd-virmidi.conf
```

## Powiązane odkrycia (z testu na sprzęcie 2026-06-02)

- **PACER ma dwa porty USB**: MIDI1 (48:0) niesie wybór utworu/preset (**Program Change**
  na ch13 boss / ch14 M:S / ch1 MicroFreak) + CC; **MIDI2 (48:1) niesie nuty** — i to na
  MIDI2 jest **przycisk start nagrania = Note 95**. Dlatego listener musi czytać **oba**
  porty PACER i forwardować je do mostu, inaczej trigger record nie dociera do Bitwiga.
- **Deferred question „PC czy CC do wyboru utworu?" → Program Change.** Filtr PC w
  listenerze łapie zmianę → live view (R3) działa.
- **Re-subskrypcja Bitwiga** po restarcie paternologii: Bitwig słucha sprzętowego
  `hw:Virmidi`, który trwa niezależnie od paternologii — link most→virmidi wraca sam po
  restarcie usługi. `snd-virmidi` zastępuje rozważany fallback i jest teraz ścieżką główną
  dla Bitwiga.

## Weryfikacja

```bash
aconnect -l | grep -iA1 "PACER MIDI"        # oba porty → klienci paternologii
journalctl --user -u paternologia -n 20 | grep -i "virmidi\|listener started"
curl -s localhost:8000/health               # pacer_input_open + bridge_port_active = true
```

Potwierdzone na żywo: PACER → paternologia (MIDI1+MIDI2) → most → virmidi → Bitwig;
zmiana utworu (PC/CC) i trigger record (Note 95) docierają, zero EBUSY, bez ręcznego kleju.

## Powiązania

- Rewiduje **KTD1** planu 001 (open_virtual_port był niewystarczający dla Bitwiga).
- [Plan 001 — orkiestracja](../plans/2026-05-31-001-feat-midi-recording-orchestration-plan.md)
- [Audio: Bitwig/PipeWire/USB](2026-06-01-bitwig-pipewire-44100-usb-audio-contention.md)
