---
date: 2026-06-04
topic: live-operator-quick-actions
refined: 2026-06-04
---

> **Aktualizacja 2026-06-04 (podczas /ce:work — ustalanie niewiadomych).** Po zbadaniu
> realnego środowiska (aktywny profil OBS `live` = `hybrid_mp4` do `/home/wojtas`; nagrania
> reorganizowane w foldery `~/Wideo/obs/<timestamp>/`; `fermata` kasuje cały folder przez
> nieodwracalne `remove_dir_all`) operator doprecyzował intencję: kasujemy **cały katalog
> nagrania**, nie pojedynczy plik, i to **przez przeniesienie do kosza** (odwracalnie), nie
> `rm`. To zmienia R3–R6 i część Scope Boundaries (patrz znaczniki *[zaktualizowane]*).

# Szybkie akcje operatorskie sesji live (launcher + usuń ostatnie nagranie)

## Problem Frame

Podczas sesji nagraniowej (warstwa `setka-live`: Bitwig + OBS + kiosk paternologii na
dwóch monitorach) operator co jakiś czas musi wykonać akcję spoza przepływu nagrywania,
nie schodząc do terminala:

1. **Przywrócić układ okien** (`setka-live show`), gdy okna się rozjechały — to akcja
   ratunkowa, więc przycisk *wewnątrz* zakopanego okna kiosku jest bezużyteczny;
   wyzwalacz musi działać globalnie, niezależnie od tego, co jest na wierzchu.
2. **Usunąć ostatnie nagranie**, gdy ujęcie się nie udało, żeby nie zaśmiecać sesji —
   akcja destrukcyjna, więc wymaga potwierdzenia i informacji zwrotnej o tym, co znikło.

Obie akcje są wykonywane **między ujęciami** (ręce wolne, wzrok na ekranie), nie w trakcie
grania.

## Requirements

- **R1.** Globalny wyzwalacz akcji dostępny niezależnie od aktywnego okna — realizowany
  podwójnie: (a) ikona w tray z menu akcji oraz (b) globalne skróty klawiszowe GNOME na te
  same akcje. Środowisko docelowe: GNOME na X11.
- **R2.** Akcja „pokaż okna" wywołuje `setka-live show` (fire-and-forget; rezultat widać na
  ekranie, brak osobnego powiadomienia wymaganego).
- **R3.** *[zaktualizowane]* Akcja „usuń ostatnie nagranie" przenosi **cały najnowszy katalog
  nagrania** (folder `<timestamp>/` w roocie nagrań — całość: plik wideo, `metadata.json`,
  `extracted/`, `analysis/`, `blender/`) **do kosza GNOME** (`gio trash`), odwracalnie.
  „Najnowszy" = wg mtime spośród prawidłowych katalogów nagrań pod rootem (katalog zawierający
  `metadata.json` + plik wideo).
- **R3a.** *[nowe]* Root nagrań pochodzi z env `SETKA_RECORDINGS_ROOT` (konwencja jak
  `FERMATA_RECORDINGS_PATH` w fermacie), z defaultem `~/Wideo/obs` i fallbackiem `~/Videos/obs`
  (zgodnie z listą zaszytą w obsession i realną lokalizacją nagrań). **Nie** pobieramy katalogu
  z OBS WebSocket — `GetRecordDirectory` zwraca `RecFilePath` (np. `/home/wojtas`), czyli
  lokalizację surowego pliku przed reorganizacją, a nie root sfolderyzowanych nagrań.
- **R4.** Przeniesienie następuje wyłącznie po jawnym potwierdzeniu w oknie dialogowym
  (`zenity`), które **nazywa konkretny katalog** (nazwa + wiek + łączny rozmiar), aby operator
  upewnił się, że to właściwe nagranie.
- **R5.** *[zaktualizowane]* Po przeniesieniu pokazywane jest powiadomienie o wyniku
  (`notify-send`): co trafiło do kosza (+ podpowiedź „przywróć z Kosza/Plików"), lub że
  anulowano / nic nie znaleziono / wystąpił błąd.
- **R6.** *[zaktualizowane]* Bezpieczeństwo operacji zapewnia jej **odwracalność**
  (przeniesienie do kosza, nie skasowanie) oraz **walidacja celu** (istnieje, jest katalogiem,
  leży ściśle pod rootem, ma prawidłową strukturę nagrania), a nie twarde blokowanie podczas
  nagrywania. Twardy guard „OBS nagrywa" nie jest wymagany: nagranie w toku to surowy plik w
  innej lokalizacji (`RecFilePath`), jeszcze nie sfolderyzowane, więc nie jest kandydatem;
  a nawet błędne przeniesienie jest odwracalne.
- **R7.** Akcja nie wykonuje żadnego resetu rigu (Bitwig / M:S / Freak / Boss) — to jest
  świadomie poza zakresem tej iteracji (patrz Scope Boundaries i przyszła faza).

## Success Criteria

- Jedno naciśnięcie skrótu **lub** jedno kliknięcie w tray przywraca układ okien przez
  `setka-live show` bez dotykania terminala.
- Akcja przenosi do kosza dokładnie zamierzony, najnowszy **katalog nagrania**, wyłącznie po
  potwierdzeniu, które jednoznacznie identyfikuje folder (nazwa + wiek + rozmiar); wynik jest
  widoczny w powiadomieniu, a operacja jest odwracalna (przywrócenie z kosza).
- Operator nie musi pamiętać żadnej komendy ani ścieżki do katalogu nagrań.

## Scope Boundaries

- **Brak resetu rigu** w tej iteracji: żadnego czyszczenia nagranych ścieżek w Bitwigu ani
  re-wyboru patternów/presetów na M:S/Freak/Boss. (Świadomie odłożone — „fajnie byłoby",
  nie krytyczne; wymaga osobnego researchu.)
- **Brak utrwalania stanu** „ostatniego nagrania" — identyfikacja wyłącznie po mtime katalogu
  nagrania w roocie (bezstanowo; odporne na restart).
- *[zaktualizowane]* **Przenosimy cały katalog nagrania do kosza** (`extracted/`, `analysis/`,
  `blender/` itd. razem z plikiem wideo i `metadata.json`) — poprzednia granica „tylko surowy
  plik" została świadomie zniesiona przez operatora. Operacja jest **odwracalna** (kosz GNOME),
  więc nie jest to nieodwracalne kasowanie.
- *[nowe]* **Brak twardego kasowania (`rm`)** — wyłącznie przeniesienie do kosza. Brak
  permanentnego opróżniania kosza przez tę funkcję.
- *[nowe]* **Logika w warstwie `setka-live` (bash), nie w paternologii** — ponieważ po
  doprecyzowaniu funkcja nie potrzebuje OBS (root z env, brak guardu „nagrywa", brak sidecara),
  znika powód, dla którego logika miała żyć w serwerze paternologii. Cała funkcja to czysty
  wrapper bash (find newest dir → zenity → `gio trash` → notify).
- **Tylko GNOME/X11** — bez wsparcia Wayland / innych DE w tej iteracji.

## Key Decisions

- **Tray + skróty, oba na tych samych akcjach** (wybór operatora) — maksimum wygody kosztem
  większej infrastruktury; zaakceptowane świadomie.
- **Kiosk odrzucony jako dom akcji** — `setka-live show` to akcja ratunkowa na rozjechane
  okna, więc przycisk w (zakopanym) oknie kiosku nie spełniłby celu.
- **Identyfikacja „ostatniego" po mtime katalogu** (wybór operatora) — prostsze i bezstanowe;
  ryzyko trafienia w zły folder zneutralizowane przez odwracalność (kosz) + walidację struktury.
- *[zaktualizowane]* **Przeniesienie do kosza zamiast `rm`** (decyzja operatora: „przesuwaj
  folder + informuj, bez guard") — bezpieczeństwo przez odwracalność i dobry UX (przywracalne z
  Nautilusa), zamiast ciężkiej maszynerii guardów. Mechanizm: `gio trash` (natywny kosz GNOME,
  zweryfikowany na maszynie). Świadomie lepsze niż istniejące `remove_dir_all` w fermacie.
- *[zaktualizowane]* **Root nagrań z env `SETKA_RECORDINGS_ROOT`** (porównanie plik vs env: env
  to ustalona konwencja u wszystkich konsumentów — `FERMATA_RECORDINGS_PATH`,
  `PATERNOLOGIA_DATA_DIR`; nikt nie trzyma roota w pliku-configu). Default `~/Wideo/obs`,
  fallback `~/Videos/obs`.
- **Akcje jako podkomendy `setka-live`, tray i skróty jako cienkie wyzwalacze** (DRY/KISS) —
  pojedyncze źródło prawdy; tray i skrót tylko odpalają komendę. `setka-live show` już istnieje;
  „usuń ostatnie" jako podkomenda `setka-live delete-last` (implementacja: przeniesienie do
  kosza). Spójne z wzorcem operatorskim w `deploy/live/`.

## Dependencies / Assumptions

- `zenity`, `notify-send`, `gio` dostępne w środowisku GNOME — **zweryfikowane na maszynie
  docelowej** (zenity 4.0.1, notify-send 0.8.3, gio 2.80 z działającym backendem kosza gvfs).
- Root nagrań ustalany z env `SETKA_RECORDINGS_ROOT` (default `~/Wideo/obs`) — **bez** zależności
  od OBS WebSocket (patrz R3a). Nagrania w roocie to sfolderyzowane katalogi `<timestamp>/` z
  `metadata.json` (reorganizacja po stopie nagrania — potwierdzone świeżymi folderami z dziś).

## Outstanding Questions

### Resolve Before Planning

- _(brak — nic nie blokuje planowania)_

### Rozstrzygnięte (podczas planowania / /ce:work 2026-06-04)

- [R3] Cel = cały katalog nagrania, przeniesiony do kosza (`gio trash`), nie pojedynczy plik.
- [R3a] Root nagrań z env `SETKA_RECORDINGS_ROOT` (default `~/Wideo/obs`, fallback `~/Videos/obs`);
  nie z OBS WebSocket.
- [R6] Bezpieczeństwo przez odwracalność + walidację, nie przez guard „OBS nagrywa" → OBS w ogóle
  niepotrzebny → logika w bashu (`setka-live`), nie w paternologii.
- [R1] Tray: PyGObject GTK3 + AyatanaAppIndicator3; skróty: `gsettings` media-keys
  (zweryfikowane na maszynie). Domyślne skróty: `Super+Shift+S` (show), `Super+Shift+D`
  (delete-last). Instalacja w `deploy/live/install.sh`.

### Deferred to Planning

- [Affects R2] Czy launcher ma eksponować więcej komend niż `show` i usuwanie (np. `restart`,
  `status`)? Domyślnie startujemy z dwiema akcjami, struktura rozszerzalna.

### Future Phase (poza tą iteracją — „reset rigu")

- [Needs research] Czyszczenie nagranych ścieżek w Bitwigu — skrypt kontrolera Bitwiga
  (rozszerzenie Java/JS) reagujący na dedykowaną wiadomość MIDI, vs wysyłanie Ctrl+Z do okna.
- [Needs research] Routing MIDI z paternologii bezpośrednio do sprzętu (M:S/Freak/Boss),
  żeby re-wysłać zdefiniowane w utworze akcje (re-wybór presetu/patternu). Uwaga: paternologia
  nie zna stanu gałek — „reset" oznacza tylko re-wybór patternu, nie przywrócenie pełnego
  stanu sprzętu. Ostrzeżenie o cegłowaniu Pacera nie dotyczy (reset nie zmienia konfiguracji
  Pacera).

## Next Steps

→ `/ce:plan` dla strukturalnego planu implementacji (iteracja 1: launcher + usuwanie
ostatniego `.mkv`). Reset rigu zaplanować osobno po researchu.
