# Handoff: launchpad-rc600

Przekazanie pracy z sesji w `~/dev/midimatrix` (2026-11-01). Ta sesja zrobiła brainstorm i plan. Kod jeszcze nie istnieje.

## Cel

Laptop tłumaczy pady Launchpad Mini (1. gen.) na CC dla Boss RC-600:
- głośność 6 pętli (pionowe fadery),
- Track FX A–D on/off.

Najpierw testy na **wirtualnym RC-600** (program TUI z własnym portem MIDI). Prawdziwy RC-600 podłączymy później.

## Dokumenty w tym repo

- Wymagania: `docs/brainstorms/2026-11-01-launchpad-rc600-requirements.md` (R1–R12, granice zakresu, decyzje)
- Plan: `docs/plans/2026-11-01-001-feat-launchpad-rc600-translator-and-simulator-plan.md` (7 jednostek, scenariusze testów)
  - Plan jest zapisany. Nie przeszedł jeszcze kroku „confidence check” ani `document-review`.

## Następny krok

`/ce:work docs/plans/2026-11-01-001-feat-launchpad-rc600-translator-and-simulator-plan.md`

Repo nie ma jeszcze kontroli wersji ani `pyproject.toml`. Jednostka 1 planu to tworzy (`uv init`, jj, a jeżeli jj nie jest dostępne, git).

## Fakty sprawdzone na sprzęcie (ta sesja)

- Launchpad Mini: USB `1235:0036`, klient ALSA 44 `Launchpad Mini`, port `hw:7,0,0`. Numer karty i numer klienta mogą się zmienić, więc szukaj portu po nazwie.
- Pady wysyłają Note on/off na kanale 1, velocity 127, `nuta = wiersz × 16 + kolumna`, wiersz 0 jest na górze.
- Prawe okrągłe przyciski to nuty 8, 24, …, 120. Górne okrągłe przyciski to CC 104–111.
- Dioda: Note on, velocity = `16 × zielony + czerwony + 12` (każda składowa 0–3). `0x0F` = czerwony, `0x3C` = zielony, `0x3F` = bursztyn. `B0 00 00` gasi wszystkie diody.
- Działający przykład animacji diod: `/tmp/claude-1000/-home-wojtas-dev-midimatrix/9fe4255b-b048-4cb1-9fbb-823f58d08a2d/scratchpad/launchpad_anim.sh` (plik tymczasowy, może zniknąć).

## Fakty o RC-600 (wiki + manual)

- `RX CH CTL = 13`: jeden kanał dla Program Change i CC. Pacer wysyła na kanale 13 CC 1–4, które zajmują sloty ASSIGN 1–4.
- ASSIGN: 16 slotów na pamięć. SOURCE akceptuje tylko `MIDI CC#01–31` i `CC#64–95`.
- Manual: `~/dev/music-box-wiki/raw/extracted/RC-600_Manual.txt`, sekcja ASSIGN mniej więcej w liniach 1454–1720.
  - `TRK1–6 LEVEL` = PLAY LEVEL 0–200.
  - Target dla Track FX ma nazwę **`T FX A–D`**, nie „TRK FX A–D” jak w dokumencie wymagań. Działa na aktualnie wybranym banku FX.
  - Manual nie podaje progu on/off dla CC ani sposobu zaokrąglania poziomu. Plan wysyła tylko wartości 0 i 127 dla FX. Oba punkty trzeba sprawdzić na prawdziwym urządzeniu.

## Decyzje użytkownika

- Nowe repo zamiast midimatrix.
- Wirtualny RC-600 jako TUI.
- Układ: 6 pionowych faderów (kolumny 1–6), FX w kolumnach 7–8, górne 2 wiersze.
- Tylko Track FX A–D (bez Input FX). Budżet slotów: 4 (Pacer) + 6 + 4 = 14 z 16.
- Przy starcie tłumacz wysyła stan początkowy: poziomy 100, FX off.
- Decyzje z planu (do potwierdzenia przez użytkownika, jeżeli zechce): CC 64–69 → `TRK1–6 LEVEL`, CC 70–73 → `T FX A–D`, sloty 5–14, jeden plik `assign.toml`, Python + uv + mido/python-rtmidi + rich.

## Zasady pracy z użytkownikiem (z ~/.claude/CLAUDE.md)

- Pisz po polsku. Każda odpowiedź zaczyna się od zwrotu z imieniem Wojciech i haiku po polsku.
- TDD. Testy jednostkowe, integracyjne i e2e są obowiązkowe. Bez mocków: testy używają prawdziwych portów ALSA.
- Każdy plik z kodem zaczyna się od dwóch linii `ABOUTME:`.
- Fail fast: w przypadku wątpliwości zapytaj, nie stosuj obejść.
- Commity w formacie conventional commits. Nigdy nie używaj `--no-verify`. Commituj tylko wtedy, gdy użytkownik o to poprosi.

## Osobne zadanie (poza tym repo)

W `~/dev/music-box-wiki` informacje o LCXL3 są **nieaktualne** (wypowiedź użytkownika). Użytkownik jeszcze nie powiedział, co dokładnie się zmieniło. Najpierw o to zapytaj. Pliki z największą liczbą wzmianek:
- `wiki/devices/Novation Launch Control XL 3.md`
- `wiki/workflows/Setup live — dual mode z bez kompa.md`
- `wiki/concepts/ASSIGN — RC-600 mapping.md`
- `wiki/connections/MIDI routing — main rig.md`
- `wiki/troubleshooting/CTL channel — Pacer vs LCXL3.md`
- `wiki/software/Paternologia.md`

Strona ASSIGN ma też sprzeczność: raz podaje „RX CTL CH = 1”, a gdzie indziej 13. Prawidłowa wartość to 13.

## Aktualizacja 2026-11-01: host docelowy lubudu

- Programy działają na lubudu (Void, i686, Python 3.13). Testy działają lokalnie.
- Plan ma nową jednostkę 0 (spike: kompilacja `python-rtmidi` na lubudu) i jednostkę 8 (wdrożenie na lubudu).
- Jednostka 0 czeka, aż na lubudu skończy się aktualizacja systemu (`xbps-install` jest zablokowany).
- Plan przeszedł `document-review` (4 persony). Wszystkie ustalenia są rozstrzygnięte i wpisane do planu: FX = blok 2×2, stan startowy symulatora „unknown”, pierwszy test na RC-600 to krótkie potwierdzenie `T FX` z SOURCE MODE = MOMENT.
- Następny krok: `/ce:work` dla jednostek 1–7 (lokalnie). Jednostka 0 czeka na lubudu.

## Aktualizacja 2026-11-01: jednostki 1–7 gotowe

- Kod jest w repo jj (commity per jednostka). `uv run pytest -q` daje 244 testy: unit, integracyjne i e2e na prawdziwych portach ALSA.
- Programy: `uv run rc600-sim [--plain]` oraz `uv run lp-rc600 --out "RC-600 SIM"`. Opis jest w `README.md` (arkusz ASSIGN, test ręczny, kontrole na RC-600).
- Testy nie mogą działać, gdy działa ręcznie uruchomiony `rc600-sim` (stała nazwa portu „RC-600 SIM”).
- Do sprawdzenia na sprzęcie: dioda „off” ma velocity 12. Kolory FX: czerwony = on, ciemny zielony = off (decyzja użytkownika).
- Następny krok: Unit 0 i Unit 8 na lubudu, gdy skończy się aktualizacja systemu. Potem test ręczny z fizycznym Launchpadem.

## Aktualizacja 2026-11-01: lubudu działa

- Po aktualizacji systemu lubudu ma Python 3.14.8. Projekt jest przypięty do 3.14 (decyzja Wojciecha). Lokalnie uv 0.7.13 ma tylko 3.14.0b2; po `uv self update` warto przejść na stabilne 3.14.
- Na lubudu: `uv` 0.7.13 i686 w `~/.local/bin`, zainstalowany `python3-devel` (potrzebny do budowy `python-rtmidi`). Kod kopiujemy przez `rsync` (bez .venv/.jj), potem `uv sync --no-dev --python /usr/bin/python3`.
- `rc600-sim` i `lp-rc600` działają na lubudu z Launchpadem (client 20).
