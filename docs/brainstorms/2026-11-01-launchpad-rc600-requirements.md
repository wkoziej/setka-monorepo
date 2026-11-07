---
date: 2026-11-01
topic: launchpad-rc600
---

# Launchpad Mini → RC-600: sterowanie z laptopa i wirtualny RC-600

## Problem Frame

Wojciech chce sterować Boss RC-600 z Launchpad Mini (1. generacja) podłączonego do laptopa:
- głośność 6 pętli,
- włączanie i wyłączanie Track FX A–D.

Launchpad nie może sterować RC-600 bezpośrednio:
- Launchpad wysyła nuty na kanale 1.
- RC-600 przyjmuje przez ASSIGN tylko CC 1–31 i 64–95 na kanale `RX CH CTL = 13`.
- Oba urządzenia są USB device.

Laptop musi więc tłumaczyć komunikaty. Przed podłączeniem prawdziwego RC-600 Wojciech chce sprawdzić i debugować układ i logikę na **wirtualnym RC-600**. Wirtualny RC-600 to program na laptopie, który odbiera te same komunikaty co prawdziwy Boss i pokazuje, co Boss by zrobił.

## Requirements

**Tłumacz (Launchpad → RC-600)**
- R1. Układ siatki 8×8:
  - Kolumny 1–6 to pionowe fadery ścieżek TRK1–6. Wiersz wybiera jeden z 8 poziomów: dolny wiersz to poziom 0, górny wiersz to poziom 100.
  - Kolumny 7–8, górne 2 wiersze (blok 2×2): przełączniki Track FX A–D. Wiersz 1: A, B. Wiersz 2: C, D.
- R2. Naciśnięcie padu fadera wysyła CC z wartością poziomu na kanale 13. Diody kolumny pokazują słupek do wybranego wiersza.
- R3. Naciśnięcie padu FX zmienia stan FX na przeciwny i wysyła **jawną wartość** (on albo off), a nie impuls „toggle”. Dioda pokazuje stan: on albo off.
- R4. Po uruchomieniu tłumacz wysyła stan startowy (wszystkie poziomy 71, czyli ok. 70%, wszystkie FX off; zmiana ze 100 na prośbę Wojciecha po teście z Launchpadem) i ustawia diody tak, żeby pokazywały ten stan.
- R5. Wszystkie numery CC są poza CC 1–4, bo tych numerów używa Pacer. Wszystkie numery CC mieszczą się w zakresach ASSIGN (1–31 albo 64–95).
- R6. Tłumacz nie wie, czy po drugiej stronie jest prawdziwy, czy wirtualny RC-600. Wybór celu to tylko wybór portu MIDI.
- R7. Tłumacz zapisuje w logu każdy komunikat: wejście z Launchpada i wyjście do RC-600.

**Wirtualny RC-600**
- R8. Wirtualny RC-600 to program w terminalu (TUI). Ma własny port MIDI, który tłumacz widzi jak każde inne urządzenie.
- R9. Wirtualny RC-600 ma konfigurację ASSIGN w formie podobnej do RC-600 (slot → SOURCE CC → TARGET, z TARGET MIN/MAX). Używa tylko 10 slotów: 6 × `TRKn LEVEL` i 4 × `T FX A–D`.
- R10. Wirtualny RC-600 reaguje tylko na kanał 13 i tylko na CC, które mają slot ASSIGN. Inne komunikaty pokazuje w logu jako zignorowane i podaje przyczynę: zły kanał, CC poza zakresem 1–31/64–95, brak slotu.
- R11. Ekran pokazuje 6 pasków PLAY LEVEL, stan 4 Track FX i log przychodzących komunikatów.
- R12. Wirtualny RC-600 sprawdza limity prawdziwego urządzenia: maksymalnie 16 slotów ASSIGN, sloty 1–4 zarezerwowane dla Pacera. Gdy konfiguracja łamie limit, program to zgłasza.

## Success Criteria

- Przy podłączonym Launchpadzie i wirtualnym RC-600 każdy pad fadera i FX zmienia odpowiedni stan na ekranie wirtualnego RC-600. Diody Launchpada pokazują ten sam stan.
- Błędna konfiguracja (zły kanał, CC poza zakresem, konflikt z CC Pacera, za dużo slotów) jest widoczna w logu lub na ekranie. Nie jest cicha.
- Konfiguracja ASSIGN z wirtualnego RC-600 daje się wpisać ręcznie do prawdziwego RC-600 bez zgadywania.

## Scope Boundaries

- Brak integracji z Bitwigiem (sterowanie stemami w DAW to osobny temat).
- Brak trybu live bez laptopa i brak wdrożenia na RPi / MIDIMatrix. Laptop docelowy to lubudu (zobacz Dependencies / Assumptions).
- Brak Input FX, reverse, play/stop ścieżek, rytmu i Master FX.
- Brak kontrolerów ciągłych (enkodery, parametry FX). Sterowanie FX to tylko on/off.
- Brak odczytu stanu z prawdziwego RC-600. Tłumacz zna tylko stan, który sam wysłał.
- Brak wirtualnej siatki Launchpada na ekranie. Wejście zawsze z fizycznego Launchpada.

## Key Decisions

- **Nowe repo `~/dev/launchpad-rc600`.** MIDIMatrix to router portów (aconnect, OLED, GPIO). To narzędzie tłumaczy komunikaty i symuluje RC-600, więc wspólny kod jest minimalny.
- **Budżet ASSIGN: 4 (Pacer) + 6 (fadery) + 4 (Track FX) = 14 z 16.** Zostają 2 wolne sloty. Track FX zamiast Input FX z wyboru Wojciecha.
- **Jawne wartości on/off zamiast toggle.** Przy toggle stan Launchpada i RC-600 może się rozjechać. Jawna wartość zawsze ustawia znany stan.
- **Stan startowy jest wysyłany.** Launchpad i RC-600 są zgodne od początku. Koszt: start tłumacza zmienia brzmienie na RC-600.
- **Górny pad = poziom 100 (unity), nie 200.** Pady nie dają przypadkowego wzmocnienia ponad nagrany poziom.

## Dependencies / Assumptions

- Kanał sterujący RC-600 to 13 (wiki: `CTL channel — Pacer vs LCXL3.md`, eksperyment z 2026-05-29).
- Pacer zajmuje sloty ASSIGN 1–4 (CC 1–4 → TRK1–4 REC/PLY). Informacje z wiki o LCXL3 są nieaktualne i nie zajmują slotów.
- Laptop docelowy to **lubudu** (`ssh lubudu`): ThinkPad, Void Linux, **i686 (32 bit)**, glibc, runit, systemowy Python 3.13. Na lubudu działają tłumacz i wirtualny RC-600 (TUI przez SSH). Testy automatyczne działają lokalnie, na maszynie deweloperskiej.
- Launchpad Mini 1. gen.: pady wysyłają `nuta = wiersz × 16 + kolumna`, diody działają przez velocity Note on (sprawdzone w tej sesji).

## Outstanding Questions

### Resolve Before Planning
(brak)

### Deferred to Planning
- [Affects R3][Needs research] Czy ASSIGN z TARGET `T FX A–D` przyjmuje jawne wartości on/off przez SOURCE ACT. LO/HI albo TARGET MIN/MAX? Czy wymaga SOURCE MODE `TOGGLE`? Sprawdzić w `RC-600_Manual.pdf` (str. 26–29).
- [Affects R2][Needs research] Jak RC-600 przelicza wartość CC 0–127 na PLAY LEVEL przy TARGET MIN/MAX 0–100. Na tej podstawie wybrać 8 wartości CC dla wierszy.
- [Affects R5][Technical] Konkretne numery CC dla 6 faderów i 4 FX.
- [Affects R6][Needs research] Czy RC-600 odbiera MIDI przez USB z Linuksa (port ALSA). To jest potrzebne dopiero przy prawdziwym urządzeniu.
- [Affects R4][Technical] Co robić z diodami pozostałych padów (kolumny 7–8, dolne 4 wiersze; górne i prawe okrągłe przyciski): wyłączone czy zarezerwowane.

## Next Steps

→ `/ce:plan` for structured implementation planning
