<!-- ABOUTME: Protokół weryfikacji M CFG (Preset Recall MIDI) Nektar Pacer na sprzęcie. -->
<!-- ABOUTME: Unit 1–2 planu docs/plans/2026-11-07-001-feat-paternologia-pacer-preset-load-messages-plan.md -->

# Weryfikacja M CFG na Pacerze

Data: 2026-11-07. Port: `hw:7,0,0` (PACER MIDI1), ALSA seq client 44.

## Unit 1 — bezpieczny test

### Krok 0 — izolacja

- W tle działał `paternologia.service` (bridge PACER MIDI1/MIDI2 → VirMIDI 0-0, RtMidiIn na 44:0 i 44:1).
- Zatrzymany: `systemctl --user stop paternologia.service` (stop przekroczył timeout i systemd zabił proces; `Restart=always` nie działa po jawnym stopie).
- Po teście uruchomić ponownie: `systemctl --user start paternologia.service`.

### Krok 1 — backup

- Pliki: `~/backup/pacer_20261107_163258_dump1.syx`, `~/backup/pacer_20261107_163258_dump2.syx` (request `F0 00 01 77 7F 02 7F F7`).
- Oba pliki mają 139544 B i są identyczne bajt po bajcie (`cmp`).
- 4762 ramki, wszystkie checksumy poprawne.
- 4725 ramek `CMD_SET + TARGET_PRESET`, 37 ramek `CMD_SET + TARGET_GLOBAL (0x05)`. **Pełnego pliku nie wolno wysyłać do Pacera.**
- Presety: CURRENT + A1–D6 (25 indeksów), każdy ma 189 ramek, w tym 16 ramek obiektu `0x7E`.
- Wynik: bramka STOP zaliczona.

### Krok 2 — wybór presetu testowego

`target_preset` w `data/songs/*.yaml`: A1–A6, B1–B5, D6 (D6: `test-presety.yaml`, `test-presety-2.yaml`).
Wolne według YAML: B6, C1–C6, D1–D5. Żaden preset w Pacerze nie jest pusty (wolne sloty mają presety fabryczne).

**Preset testowy: D5** (nazwa „MMC”, preset fabryczny, idx `0x17`). Zawartość jest w backupie. Po teście restore selektywny (189 ramek D5).

### Format M CFG odczytany z backupu (R2)

- **Każdy wpis M CFG = osobna ramka SysEx** (16 ramek `0x7E` na preset).
- Elementy wpisu `n`: `(n-1)*6 + 1..5` = channel, typ, data1, data2, data3. Brak elementu 6 (active).
- Kodowanie elementu jak w `build_control_step`: `elm, 0x01, val, 0x00`; ostatni element bez paddingu `0x00`.
- Pusty wpis: channel 0, typ `0x61`, data 0.

Przykład — pusty wpis 1, preset A1:

```
F0 00 01 77 7F 01 01 01 7E 01 01 00 00 02 01 61 00 03 01 00 00 04 01 00 00 05 01 00 0A F7
```

Przykład — preset A5 „Zima” (używany na żywo) ma już aktywne M CFG: 16 wpisów `0x65` (LOAD_CC), CC 123 (All Notes Off) = 127 na kanałach 1–16:

```
F0 00 01 77 7F 01 01 05 7E 01 01 01 00 02 01 65 00 03 01 7B 00 04 01 7F 00 05 01 00 07 F7
...
F0 00 01 77 7F 01 01 05 7E 5B 01 10 00 5C 01 65 00 5D 01 7B 00 5E 01 7F 00 5F 01 00 36 F7
```

To potwierdza semantykę `0x65`: data1 = numer CC, data2 = wartość, data3 = 0. Bajt kanału 1..16 wskazuje kodowanie 1-based (jak `midi_channel` w `build_control_step`) — do potwierdzenia w kroku 4.

### Krok 3 — ręczna konfiguracja D5 (wartości testowe)

| Wpis | Typ | Kanał | Dane | Uzasadnienie |
|---|---|---|---|---|
| 1 | PC (PRG BANK) | 14 (M:S) | program 5, bank 0/0 | PC do M:S, sprawdzenie Bank Select przy banku 0 |
| 2 | CC | 13 (RC-600) | CC 40 = 99 | RC-600 ASSIGN przyjmuje tylko CC 1–31 i 64–95, CC 40 nie ma efektu |
| 3 | PC (PRG BANK) | 12 (nieużywany) | program 7, bank LSB 1, MSB 2 | Bank Select przy niezerowym banku |
| 4 | NOTE | 11 (nieużywany) | nuta 60, velocity 100 | inna niż trigger OBS (ch1, nuty 93/94) |

**Zmiana względem planu (decyzja użytkownika):** wpisy nie były ustawione z panelu, tylko wysłane przez SysEx (test (f) wcześniej niż w planie).
Powód: backup dał prawdziwe ramki `0x7E` z tego egzemplarza (A5), a builder odtwarza je bajt po bajcie.

Builder (skrypt roboczy) odtwarza dokładnie ramki z backupu: A5 wpis 1, A5 wpis 16, A1 wpis 1 (pusty).
Kontrola przed wysyłką: każda ramka `CMD_SET (0x01)` + `TARGET_PRESET (0x01)` + idx `0x17` + obiekt `0x7E`, checksum poprawny, brak `0x05`.
Wysyłka: `amidi -p hw:7,0,0 --sysex-interval=20 -s d5_mcfg_test.syx` (4 ramki, 120 B):

```
F0 00 01 77 7F 01 01 17 7E 01 01 0E 00 02 01 45 00 03 01 05 00 04 01 00 00 05 01 00 7D F7
F0 00 01 77 7F 01 01 17 7E 07 01 0D 00 08 01 65 00 09 01 28 00 0A 01 63 00 0B 01 00 3A F7
F0 00 01 77 7F 01 01 17 7E 0D 01 0C 00 0E 01 45 00 0F 01 07 00 10 01 01 00 11 01 02 3E F7
F0 00 01 77 7F 01 01 17 7E 13 01 0B 00 14 01 43 00 15 01 3C 00 16 01 64 00 17 01 00 0D F7
```

### Krok 4 — dump D5 (round-trip)

- Request: `F0 00 01 77 7F 02 01 17 7F 67 F7` → 189 ramek, wszystkie `TARGET_PRESET` idx `0x17`.
- 4 wysłane ramki wracają **bajt w bajt**. Względem backupu zmieniły się tylko te 4 ramki (`0x7E` elm 01, 07, 0D, 13); pozostałe 185 ramek bez zmian.
- Wniosek: Pacer przyjmuje zapis M CFG w formacie 5 elementów (bez active) i zapisuje go w presecie. Kodowanie kanału 1-based (0 = Global, zgodnie z instrukcją s. 15).
- Uwaga techniczna: `aseqdump` subskrybujący port Pacera blokuje `amidi -r` (Device or resource busy). Wysyłka `-s` działa. Przed dumpem trzeba zatrzymać monitor.

### Krok 5 — monitor wyjścia

Obserwacja przypadkowa (16:35:57): załadowanie A5 wysłało na USB (44:0, PACER MIDI1) 16 × CC 123 = 127, kanały 1–16, odstęp ok. 1 ms. M CFG działa przy ręcznej zmianie presetu.

Pomiar 16:43–16:44 (log `aseqdump`, kanały w logu 0-based: 13 = ch14):

```
16:43:50.224  CC   ch14  CC0  = 0
16:43:50.225  CC   ch14  CC32 = 0
16:43:50.226  PC   ch14  program 5
16:43:50.227  CC   ch13  CC40 = 99
16:43:50.228  CC   ch12  CC0  = 2
16:43:50.229  CC   ch12  CC32 = 1
16:43:50.230  PC   ch12  program 7
16:43:50.230  NOTE ch11  note 60 vel 100
```

| Metoda | Wynik (USB, PACER MIDI1) |
|---|---|
| (b) `[Preset]` + D + 5 | wysłane (16:43:50) |
| (a) strzałka D4 → D5 | wysłane (16:43:58, 16:44:06 — 2/2) |
| przejście na D4 (brak M CFG) | brak wiadomości |
| (d) odłączenie/podłączenie USB | nie zmierzone na USB: monitor stracił subskrypcję przy odłączeniu (16:44:19) |
| (c) footswitch `PRSET` | pominięte (brak takiego przycisku, wymaga dodatkowego zapisu) |

Wnioski:
- Wiadomości idą w kolejności wpisów, odstęp ok. 1 ms; cała paczka 4 wpisów ≈ 6 ms.
- **PGBNK zawsze wysyła Bank Select: CC0 = data3 (MSB), CC32 = data2 (LSB), potem PC — także przy banku 0.**
- NOTE: tylko Note On, bez Note Off.
- Port i numer klienta ALSA po ponownym podłączeniu bez zmian (`hw:7,0,0`, client 44).

**DIN: M:S nie przełączył patternu** (oczekiwany A06 po PC 5 na ch14). Przyczyna do ustalenia.

### Diagnoza DIN → M:S

Przyciski (sam PC na ch14, bez Bank Select): A1 „cisza” PC 0 (A01) ✅, A5 „Zima” PC 48–51 (D01–D04) ✅, A4 „Ślimak” PC 72–75 (E09–E12) ✅ — także gdy M:S gra.
B5 „Świt” PC 82–83 (F03–F04) ❌ — osobny problem po stronie M:S / patternów F, poza zakresem M CFG (do zbadania osobno).
Wniosek: łańcuch DIN działa, M:S przyjmuje PC na ch14; numer PC (poza F) i odtwarzanie nie blokują zmiany.

Test Bank Select: wpis 1 D5 zmieniony na PGBNK ch14 program 48 (D01, wzorzec działający z przycisku Zimy).

**Obserwacja — utracony zapis:** pierwsza wysyłka tej ramki (17:32) nie została zapisana (dump D5 dwukrotnie pokazał stary wpis; CURRENT bez zmian, aktywny był A4).
Ponowiona wysyłka tej samej ramki, przy ekranie presetu (bez menu), została zapisana.
Przypuszczenie (niepotwierdzone): w czasie pierwszej wysyłki użytkownik był w menu GLBL (odczyt M OUT), a Pacer ignoruje zapis SysEx w menu.
**Wniosek dla Fazy B:** po eksporcie trzeba zweryfikować zapis dumpem presetu (read-back), bo Pacer może zignorować zapis bez sygnału błędu.

**Wynik (17:36–17:37):** po załadowaniu D5 M:S przełącza się na D01 (potwierdzone przez użytkownika, wielokrotnie). Monitor USB: CC0=0, CC32=0, PC 48 na ch14, potem pozostałe wpisy.
Wnioski:
- **M CFG jest wysyłane także na DIN** (przy obecnym `M OUT`).
- **Bank Select (CC0/CC32 = 0) przed PC nie przeszkadza M:S.**
- Brak reakcji na A06 (PC 5) w pierwszym teście nie jest problemem M CFG; przyczyna po stronie M:S jak przy „Świcie” (do zbadania osobno).

Test (d) — start po zasilaniu (17:39): D5 aktywny, M:S na innym patternie, odłączenie i podłączenie USB → **M:S nie przełączył się na D01**.
Wniosek: Pacer nie wysyła M CFG po włączeniu zasilania (przynajmniej na DIN). Pierwszy utwór po starcie trzeba wywołać zmianą presetu.
Uwaga: przy odłączaniu USB i przed dumpem Pacer wysłał na ch1 CC7/CC11 (szum, prawdopodobnie niepodłączone wejście EXP). Bez wpływu na test.

### Krok 6 — restore D5

- Plik: 189 ramek D5 wycięte z `pacer_20261107_163258_dump1.syx`; automatyczna kontrola: każda ramka `CMD_SET + TARGET_PRESET + 0x17`, checksumy poprawne, brak `TARGET_GLOBAL` (dwie niezależne kontrole).
- Wysyłka: `amidi --sysex-interval=20`, 5546 B.
- Read-back: dump D5 identyczny z backupem bajt w bajt (pomijając 3-bajtowy prefiks `B0 0B 00` = CC11 z szumu EXP, który przyszedł przed SysEx).
- `paternologia.service` uruchomiony ponownie.

## Podsumowanie Unit 1

| Pytanie | Odpowiedź |
|---|---|
| Format SysEx M CFG (R2) | Obiekt `0x7E`, ramka na wpis, 5 elementów (channel 0=Global/1–16, typ, data1–3), bez active. Zapis przyjmowany i zwracany bajt w bajt. |
| `0x65` LOAD_CC | data1 = CC, data2 = wartość (potwierdzone dumpem A5 i monitorem) |
| `0x45` PGBNK | wysyła zawsze CC0 = data3 (MSB), CC32 = data2 (LSB), potem PC = data1 |
| `0x43` NOTE | tylko Note On (data1 = nuta, data2 = velocity) |
| Kiedy M CFG się wysyła (R3) | (a) strzałki ✅, (b) `[Preset]`+bank+numer ✅, (c) `PRSET` — nie testowane, (d) zasilanie ❌ |
| Wyjścia | USB ✅, DIN ✅ (M:S reaguje) |
| Bank Select a M:S | CC0/CC32 = 0 przed PC nie przeszkadza |
| Kolejność / tempo | kolejność wpisów, ok. 1 ms między wiadomościami |
| Bezpieczeństwo | jedyne zapisy: wpisy M CFG D5 (test f) i selektywny restore D5; brak `TARGET_GLOBAL`; read-back zgodny |

Ustalenia dla Fazy B:
- Eksport musi robić read-back (dump presetu i porównanie), bo Pacer potrafi zignorować zapis bez błędu.
- Na czas dumpu nie może działać subskrybent ALSA seq na porcie Pacera (bridge Paternologii / `aseqdump`) — `amidi -r` dostaje „Device or resource busy”.
- Pacer nie wysyła M CFG po starcie — nie polegać na tym przy pierwszym utworze.

Otwarte poza zakresem: M:S nie reaguje na PC 5 (A06) ani PC 82–83 (F03–F04) z przycisków „Świtu”, a reaguje na PC 0, 48–51, 72–75.

## Unit 2 — test przydatności (rig end-to-end)

Bridge Paternologii zatrzymany na czas testu.

**Utwór wzorcowy: „Zima” (A5).** Stan startowy = akcje-stany z SW1 („presety i nabij beat”) bez CC1 (nagrywanie track 1 to akcja, nie stan).
Metoda zmiany presetu na żywo: strzałki `[C]/[D]` i `[Preset]`+bank+numer — obie działają (Unit 1).
Memory RC-600 wybiera PC na ch13 (akcja `boss: preset`; wyświetlana wartość = surowa + 1).

| Preset | RC-600 (ch13) | M:S (ch14) | MicroFreak (ch1) |
|---|---|---|---|
| D5 („Zima” SW1) | PC 3 → MEM 4 | PC 48 → D01 | PC 67 → preset 68 |
| D4 (kontrast, „Zima” SW2 + inna memory) | PC 5 → MEM 6 | PC 49 → D02 | PC 68 → preset 69 |

Zapis: wpisy 1–3 przez SysEx, read-back OK dla D4 i D5. Pozostałe wpisy OFF. Po teście restore D4 i D5 z backupu.

### Wyniki Unit 2

- **Monitor USB (17:47–17:50):** 55 załadowań D4/D5 (29 × D5, 26 × D4), każde z kompletną paczką 3 wiadomości w kolejności RC-600 → M:S → MicroFreak, maks. 6 ms na paczkę, 0 strat, brak innych zdarzeń.
- **A (10 przełączeń D4↔D5):** RC-600, M:S, MicroFreak w stanie docelowym 10/10 (potwierdzone przez użytkownika).
- **B (seria szybkich przełączeń):** wszystkie 3 urządzenia w stanie ostatniego presetu.
- **C (pętla grająca na RC-600):** RC-600 zmienia memory; brak niezamierzonych akcji.
- **Numeracja:** wyświetlacze zgodne z `preset_display_offset: 1` (PC 3 → MEM 4, PC 67 → MicroFreak 68).
- **Live view (17:56, bridge włączony):** każde załadowanie D5 i D4 → `MIDI → song 'zima'`.
  Uwaga: jedna paczka daje do 2 zdarzeń „song” (PC RC-600 ch13 = 3 i PC MicroFreak ch1 = 67 — oba w indeksie Zimy). D4 też wskazuje Zimę (PC 68 = MicroFreak z SW2 Zimy).
- **Bitwig:** nie testowane (Bitwig nie był uruchomiony).
- **OBS:** nie działał; tracebacki w logu usługi to pętla ponownego łączenia z OBS, bez związku z testem.

Restore D4 i D5: 189 ramek każdy z backupu, kontrola braku `TARGET_GLOBAL`, read-back zgodny dla obu. `paternologia.service` uruchomiony ponownie.

### Werdykt: **GO**

(1) M CFG wysyła się przy metodach zmiany presetu używanych na żywo (strzałki, `[Preset]`+bank+numer); (2) wszystkie 3 urządzenia w stanie docelowym 10/10; (3) brak niezamierzonych akcji RC-600.

Uwagi do Fazy B:
- Read-back po eksporcie (Pacer potrafi zignorować zapis bez błędu).
- Na czas eksportu z read-backiem trzeba odłączyć subskrybenta ALSA seq od portu Pacera (bridge).
- Kilka akcji `PRESET` w `on_load` daje kilka zdarzeń live view na jedno załadowanie — wynik ten sam, gdy wszystkie wskazują ten sam utwór.
- M CFG nie wysyła się po włączeniu zasilania.

## Unit 3 — builder M CFG i round-trip

- `PacerSysExBuilder.build_midi_config_entry` / `build_empty_midi_config_entry` odtwarzają bajt w bajt ramki z dumpu (A5 wpis 1 i 16, A1 pusty wpis 1, D5 wpis 3 z round-tripu) — testy w `tests/test_pacer_sysex.py`.
- Round-trip ramek z tego samego układu: Unit 1 krok 4 (4 ramki D5, bajt w bajt).
- **(f) zapis SysEx a wysyłka M CFG:** monitor działał w czasie pierwszego zapisu do D5 (16:39:14, monitor do 16:39:38) — brak zdarzeń. Zapis do presetu, który nie jest aktywny, nie wyzwala M CFG. Zapis do aktywnego presetu nie był testowany.
- **Checksum:** Paternologia liczyła checksum od Manufacturer ID (przesunięcie o 9 względem Pacera). Pacer nie sprawdza checksumy, więc eksport działał. Poprawione w osobnym commicie: checksum od bajtu CMD; round-trip eksportu „Zimy” na D5 — 78/78 ramek (poza nazwą) bajt w bajt, potem restore D5 z read-backiem.
- Ramka nazwy presetu w dumpie ma inny układ niż wysyłana przez Paternologię (Pacer zwraca element `0x01` z długością; Paternologia wysyła element `0x00`). Nazwa zapisuje się poprawnie — poza zakresem.

## Unit 5 — eksport z on_load (round-trip)

„Zima” z `on_load` = stan SW1 (RC-600 PC 3, M:S d01, MicroFreak PC 67), eksport na D5: 95 ramek (16 × `0x7E`), wszystkie `TARGET_PRESET` idx `0x17`.
Dump D5: 94/94 ramki poza nazwą bajt w bajt. Restore D5 z backupu, read-back zgodny.

## Unit 5 — read-back po wysyłce

`POST /pacer/send/{song_id}` po `amidi -s` robi dump presetu i porównuje ramki (bez nazwy). Na czas dumpu listener zwalnia wejścia Pacera (`MidiListener.paused()`), a `poll_reconnect` ich nie otwiera.
Test w działającej usłudze (18:59): „Zima” → D5, odpowiedź `verified: true`, listener wstrzymany 2,3 s (18:59:33,4–18:59:35,7), całe żądanie 5,2 s. Restore D5 z read-backiem zgodny.
