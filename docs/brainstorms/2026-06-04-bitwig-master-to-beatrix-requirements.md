---
date: 2026-06-04
topic: bitwig-master-to-beatrix
---

# Bitwig master → beatrix: handoff zmiksowanego audio do analizy

## Problem Frame
Po dostrojeniu utworu w Bitwig droga dźwięku do miejsca, w którym beatrix go analizuje
(a analiza napędza animacje w cinemon), jest w pełni ręczna i podatna na błędy:
folder docelowy eksportu trzeba za każdym razem wyklikać, a istniejący „Analizuj"
(fermata → beatrix) patrzy dziś **tylko do `extracted/`**, nie do polerowanego
`mixed/`, i przy pustym `extracted/` **cicho failuje**. Wojtas chce jak najmniej
ręcznej roboty teraz, a jednocześnie otwartą drogę do analizy **poszczególnych
ścieżek (stemów)** w przyszłości — pod per-strip targeting animacji w cinemon.

Rurociąg jest już w dużej części gotowy: kanoniczny `mixed/` istnieje w
`RecordingStructureManager`, a cinemon jest „master-aware" (preferuje
`analysis/{stem}_analysis.json` pasujący do `--main-audio`). Brakuje ostatniej mili:
konwencji zapisu i tego, by „Analizuj" widział `mixed/`.

## Requirements
- R1. `RecordingStructureManager` zyskuje kanoniczny katalog `bitwig/` (obok
  `extracted/`, `mixed/`, `analysis/`, `blender/`) jako stały dom na projekt Bitwig
  (Save As tutaj). Tworzony przez `create_structure`, wystawiony w
  `RecordingStructure`. Wzorzec analogiczny do `blender/`.
- R2. Master powstaje przez Bitwig **Export Audio (Project Master)** i ląduje w
  `mixed/master.wav`. Stemy (opcjonalnie, przyszłość) lądują w `mixed/stems/*.wav`
  (Export Audio potrafi eksportować pojedyncze ścieżki jednym ruchem). To konwencja
  operatorska, nie kod — kod musi ją tylko respektować (R3).
- R3. Akcja „Analizuj" (przycisk w fermacie + ścieżka beatrix) **iteruje po plikach
  audio w `mixed/`** — `mixed/master.wav` oraz pliki w `mixed/stems/` — produkując
  jedną `analysis/{stem}_analysis.json` per plik. Preferuje `mixed/` nad `extracted/`;
  gdy `mixed/` puste, fallback do `extracted/` (zgodność wstecz). Logika iteruje po
  zbiorze plików, więc n=1 (sam master) to dzisiejszy przypadek, a dorzucenie stemów
  później nie wymaga zmian w kodzie.
- R4. Akcja „Analizuj" **pokazuje błąd w UI zamiast cicho failować**, gdy nie ma nic
  do analizy (naprawa znanego cichego faila fermaty przy pustym wejściu).

## Success Criteria
- Po Export Audio do `mixed/master.wav` jedno kliknięcie „Analizuj" w fermacie tworzy
  `analysis/master_analysis.json`, a `cinemon-blend-setup` sam go podchwytuje
  (selekcja master-aware już istnieje).
- Wrzucenie stemów do `mixed/stems/` i kliknięcie „Analizuj" tworzy po jednej analizie
  per stem — bez zmian w kodzie.
- Gdy nie ma czego analizować, fermata pokazuje czytelny komunikat błędu (nie milczy).

## Scope Boundaries
- **Bez watchera / daemona** — świadomie odrzucone. Eksport zostaje ręcznym
  kliknięciem w Bitwig; analiza odpalana przez istniejący przycisk/komendę.
- **Bez skryptowania Bitwig / controller extension / automatycznego eksportu** —
  potwierdzone jako niewykonalne: brak headless renderu, brak akcji „Export Audio"
  w API, brak per-project ścieżki eksportu. Krok Export Audio pozostaje ręczny w GUI.
- **Bez auto-kopiowania z podfolderów projektu Bitwig** (`master-recordings/`,
  `bounce/`) — master przychodzi przez Export Audio do `mixed/`. Czytanie z
  `bitwig/<proj>/master-recordings|bounce/` to ewentualne przyszłe ułatwienie.
- **Per-strip *targeting* animacji w cinemon** (mapowanie stripów na analizy stemów)
  to przyszła robota po stronie cinemon; ten brainstorm odblokowuje jedynie
  *analizę* poszczególnych ścieżek.
- Korekta dryfu audio/wideo zostaje ręczna w Blenderze.

## Key Decisions
- **Export Audio (offline) zamiast master-recording/bounce (realtime):** szybsze,
  standardowe, już udokumentowane w `music-box-wiki`. Friction „gdzie zapisać"
  rozwiązujemy po stronie setki, nie Bitwig (Bitwig i tak nie da się tu pomóc
  skryptem — ścieżka eksportu „lepi się" w obrębie sesji, więc per-song wskazujesz raz).
- **„Analizuj" iteruje po `mixed/` (master + stemy) już teraz:** kupuje przyszłą
  analizę per-stem niemal darmo (pętla zamiast pojedynczego pliku).
- **Formalizacja `bitwig/`:** tanie (kopia wzorca `blender/`), daje kanoniczny dom na
  projekt i otwiera furtkę do czytania wyjść projektu w przyszłości.

## Dependencies / Assumptions
- cinemon już preferuje `analysis/{stem}_analysis.json` pasujący do `main_audio`
  (potwierdzone w `cinemon_config_generator.py`).
- Bitwig Export Audio pamięta ostatni folder w obrębie sesji (wskazujesz `mixed/`
  raz na utwór).
- Zakłada się: jedno nagranie = jeden utwór/projekt.
- Infra plikowa (`mixed/`, `ensure_mixed_dir`) już istnieje w setka-common.

## Outstanding Questions

### Resolve Before Planning
- (brak — decyzje produktowe rozstrzygnięte)

### Deferred to Planning
- [Affects R3][Technical] Gdzie żyje iteracja: rozszerzyć CLI beatrix o przyjmowanie
  katalogu, czy zostawić beatrix per-plik i zrobić pętlę w fermacie/helperze?
- [Affects R3][Technical] Reguły nazewnictwa/kolizji `*_analysis.json` przy stemach
  o podobnych nazwach; jak nazwy stemów mapują się na targety stripów w cinemon.
- [Affects R4][Technical] Dokładna ścieżka propagacji błędu backend→frontend w
  fermacie (naprawa cichego faila).
- [Affects R1][Needs research] Czy któryś konsument zakłada, że istnieją tylko
  `extracted/`/`mixed/`? Idempotencja `create_structure` dla istniejących nagrań
  (dodanie `bitwig/` wstecz).
- [Affects R2][Needs research] Opcjonalnie: czy `AudioValidator` ma też rozwiązywać
  master z `bitwig/<proj>/master-recordings|bounce/` jako fallback? (odroczone ułatwienie)

## Next Steps
→ `/ce:plan` — strukturyzowane planowanie implementacji
