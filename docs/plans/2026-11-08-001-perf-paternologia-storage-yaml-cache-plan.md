---
title: "perf(paternologia): cache YAML w Storage i lżejsza przeglądarka kiosku"
type: refactor
status: active
date: 2026-11-08
---

# perf(paternologia): cache YAML w Storage i lżejsza przeglądarka kiosku

## Overview

Dwie niezależne optymalizacje paternologii na hoście lubudu:

1. **Backend:** dodajemy do `Storage` cache sparsowanych plików YAML. Klucz unieważnienia to `mtime_ns` i rozmiar pliku. Cel: `GET /` skraca się z ok. 840 ms do < 100 ms.
2. **Kiosk:** sprawdzamy lżejszą przeglądarkę na silniku WebKitGTK zamiast Firefoksa i przełączamy kiosk, jeśli pomiar to uzasadni. Cel: wyraźnie mniej RAM i CPU w spoczynku.

Nie zmieniamy języka, frameworka, frontendu (HTMX) ani formatu danych.

## Problem Frame

Pomiary na lubudu (ThinkPad X60s, Core Duo i686, 2 GB RAM, Python 3.11, 2026-11-08):

| Pomiar | Wynik |
|---|---|
| `GET /` z rozgrzanym serwerem | ~840 ms (pierwsze żądanie: 2,6 s) |
| `yaml.safe_load` wszystkich plików (14 utworów + devices + order) | ~830 ms |
| `get_songs()` + `get_devices()` | ~945 ms |
| `yaml.__with_libyaml__` | `False` (brak wheela PyYAML z libyaml dla i686) |

Prawie cały czas odpowiedzi to parsowanie YAML w czystym Pythonie. `Storage` czyta i parsuje pliki przy **każdym** wywołaniu `get_*`. Pojedyncze żądanie często woła kilka takich metod (np. `get_songs()` i `get_devices()`). Dane zmieniają się rzadko: przez zapis z UI, przez ręczną edycję plików w `data/` albo przez auto-deploy. Auto-deploy (cron `*/2` z `~/paternologia/bin/autoupdate.sh`, skrypt tylko na hoście) robi `git reset --hard` i uruchamia `deploy/remote/install.sh`, który restartuje uvicorn (`pkill`). Po deployu cache jest więc zawsze pusty.

Przepisanie aplikacji na inny język odrzuciliśmy. Ten sam zysk daje mała zmiana w jednym module.

Drugi problem to przeglądarka w kiosku. Pomiar z 2026-11-08:

| Proces | RAM (RSS) | CPU |
|---|---|---|
| Firefox (proces główny + procesy treści) | ~900 MB łącznie | ~17–24% |
| uvicorn (paternologia) | ~40 MB | ~1,6% |

Lubudu ma 2 GB RAM. Firefox zużywa ponad 20 razy więcej pamięci niż sam serwer. Przepisanie GUI na natywne odrzuciliśmy, bo wymaga przepisania wszystkich szablonów i logiki HTMX. Lżejsza przeglądarka z tym samym URL może dać podobny zysk bez zmian w kodzie.

Przyczyna ~20% CPU Firefoksa w spoczynku jest nieznana. Możliwe źródła: strumień SSE z `routers/live.py`, animacje CSS albo koszt silnika. To hipoteza do sprawdzenia w Unit 4, nie fakt.

## Requirements Trace

- R1. Powtórny odczyt niezmienionego pliku YAML nie wywołuje ponownie parsera YAML.
- R2. Zmiana pliku na dysku przez zewnętrzny proces (głównie ręczna edycja w `data/`) jest widoczna przy następnym żądaniu, bez restartu serwera, o ile zmienia `mtime` lub rozmiar pliku. Auto-deploy restartuje serwer, więc nie zależy od R2.
- R3. Zapis przez `Storage.save_*` jest widoczny natychmiast przy następnym odczycie, także gdy `mtime` i rozmiar pliku się nie zmienią (zgrubna rozdzielczość czasu systemu plików).
- R4. Usunięty plik nie wraca z cache (`get_song`, `get_songs`, `delete_song`).
- R5. Wywołujący dostają niezależne obiekty modeli. Modyfikacja zwróconego obiektu nie zmienia danych w cache.
- R6. Publiczne API `Storage` (sygnatury i zachowanie) nie zmienia się.
- R7. Na lubudu `GET /` z rozgrzanym serwerem trwa < 100 ms (cel; weryfikacja ręczna po wdrożeniu).
- R8. Mamy porównanie RAM i CPU w spoczynku: Firefox kontra co najmniej jedna przeglądarka WebKitGTK dostępna na Void i686, z tym samym URL i na tym samym ekranie.
- R9. Jeśli przełączymy kiosk, wszystkie funkcje UI działają tak samo jak w Firefoksie: lista i edycja utworów (HTMX), widok live (SSE), eksport do Pacera, nagrywanie OBS. Kiosk startuje sam po zalogowaniu, na pełnym ekranie i bez pasków przeglądarki.

## Scope Boundaries

- Poza zakresem: `CSafeLoader` / budowa PyYAML z libyaml na Voidzie (możliwy follow-up, gdy cache nie wystarczy).
- Poza zakresem: natywne GUI (GTK, Tkinter itp.) zamiast interfejsu webowego.
- Poza zakresem: przeniesienie launchera kiosku do repo (wzór: `deploy/live/bin/paternologia-kiosk.sh` z testem `deploy/live/tests/test_kiosk_class.sh`). To możliwy osobny temat.
- Poza zakresem: diagnoza i naprawa CPU strony (SSE, CSS). Unit 4 zbiera tylko dane do tego tematu.
- Poza zakresem: zmiany w szablonach lub JS dla zgodności z WebKitGTK. Jeśli Unit 4 wykaże niezgodność, zapisujemy ją jako osobny temat.
- Poza zakresem: zmiana formatu danych, baza danych, przepisanie backendu.
- Poza zakresem: cache wyrenderowanego HTML lub odpowiedzi HTTP.

## Context & Research

### Relevant Code and Patterns

- `packages/paternologia/src/paternologia/storage.py` — wszystkie odczyty YAML idą przez `yaml.safe_load` w metodach `get_devices`, `get_songs_order`, `_load_song_file`, `get_pacer_config`, `get_obs_config`. Zapisy: `save_devices`, `save_songs_order`, `save_song`, `save_pacer_config`, `delete_song`.
- `packages/paternologia/src/paternologia/dependencies.py` — `get_storage()` trzyma jedną instancję `Storage` na proces. Cache jako atrybut instancji żyje więc przez cały czas pracy serwera.
- `packages/paternologia/src/paternologia/main.py` — `lifespan` woła `storage.get_songs()` przy starcie (budowa indeksu MIDI). Cache rozgrzeje się więc sam przy starcie i pierwsze żądanie użytkownika też będzie szybkie.
- Poza `storage.py` żaden kod w `src/` nie woła `yaml.safe_load` (sprawdzone grepem). Cała zmiana zostaje w jednym module.
- Testy: `packages/paternologia/tests/test_storage.py` (unit, fixture `temp_storage` na katalogu tymczasowym), `tests/test_api.py` (integracja przez `TestClient`), `tests/test_e2e.py` (przepływy użytkownika przez `TestClient` z podmienionym `Storage`).

### Institutional Learnings

- Brak wpisów w `docs/solutions/` o cache lub wydajności paternologii.
- Lubudu ma auto-deploy przez cron `*/2`. Sprawdzone na hoście 2026-11-08: `autoupdate.sh` po zmianie w `packages/paternologia` uruchamia `install.sh`, a ten restartuje uvicorn. Cache nie przetrwa więc deployu. R2 (unieważnienie po `mtime`) jest potrzebne dla ręcznej edycji plików przy działającym serwerze.
- Pamięć projektu: grafika GMA 945 na lubudu wymaga `xf86-video-intel` (SNA), a domyślny modesetting pada na glamor. WebKitGTK może używać akceleracji GPU, więc kompozycja może zachować się inaczej niż w Firefoksie. Sprawdzamy to w Unit 4.
- Pamięć projektu: komendy z autostartu startują z czystym środowiskiem. Launcher kiosku trzeba sprawdzić w takim środowisku, a nie tylko z terminala.

### Kiosk na lubudu (stan z 2026-11-08)

- Autostart: `~/.config/autostart/paternologia-kiosk.desktop` na hoście, poza repo. Czeka na `/health` przez `wget`, potem uruchamia `firefox --kiosk http://localhost:8000`.
- Polityki Firefoksa: `/usr/lib/firefox/distribution/policies.json` na hoście.
- Przeglądarki WebKitGTK w repo Void i686 (sprawdzone `xbps-query -R`): `surf` 2.1, `epiphany` 48.5, `luakit` 2.4, `vimb` 4.0; `libwebkit2gtk41` i `libwebkitgtk60` 2.50.4. `cog` nie jest dostępny.

## Key Technical Decisions

- **Cache trzyma wynik `yaml.safe_load` (dict/list), a nie modele pydantic.** Każdy odczyt wykonuje `model_validate` na danych z cache. Powód: modele pydantic są mutowalne. Trasy edycji mogą zmieniać zwrócone obiekty, a współdzielony obiekt z cache dałby trudne do znalezienia błędy (R5). Walidacja w pydantic-core jest dużo tańsza niż parsowanie YAML w czystym Pythonie. Aby nikt nie zmienił samego dict-a z cache, odczyt przekazuje do walidacji dane, których walidacja nie modyfikuje. Pydantic buduje nowe obiekty, więc to wystarcza dla modeli. Dla `get_songs_order` (zwraca surową listę) zwracamy kopię listy.
- **Klucz unieważnienia: `(st_mtime_ns, st_size)` z jednego `stat()`.** `stat()` kosztuje mikrosekundy, a wykrywa zmiany z zewnątrz (R2). Sam `mtime` może nie wystarczyć przy dwóch zapisach w tym samym takcie zegara, więc dodajemy rozmiar.
- **Jawne unieważnienie przy zapisie i usunięciu.** `save_*` i `delete_song` usuwają wpis dla swojej ścieżki. To zamyka lukę z R3, gdy zapis nie zmieni ani `mtime`, ani rozmiaru.
- **Jedna prywatna metoda „wczytaj YAML przez cache" dla wszystkich odczytów** (DRY). Obecne `with open(...) + yaml.safe_load` w pięciu miejscach zastępuje jedno wywołanie. Logika „plik nie istnieje → wartość domyślna" zostaje w metodach publicznych bez zmian.
- **Bez limitu rozmiaru i bez TTL.** Danych jest kilkanaście małych plików. Prosty `dict` ścieżka → wpis wystarcza (KISS). Wpisy usuniętych plików znikają przy `delete_song` albo przy odczycie przez `get_song`, gdy `stat()` zgłosi brak pliku. Wpisy plików usuniętych z zewnątrz mogą zostać w cache, bo `get_songs` bierze listę plików z `glob` i nie sprawdza brakujących plików. Nie wpływa to na wynik, a koszt pamięci jest pomijalny.
- **Bez blokad, ale z kluczem ze `stat()` przed odczytem.** Większość tras jest `async`, ale `export_syx` i `send_to_pacer` w `routers/pacer.py` to zwykłe `def`. FastAPI uruchamia je w puli wątków, więc dostęp do słownika cache bywa współbieżny. Pojedyncze operacje `get` i przypisanie na `dict` są atomowe dzięki GIL. Klucz wpisu bierzemy ze `stat()` wykonanego **przed** odczytem pliku, a wpis zapisujemy jednym przypisaniem. Wtedy wyścig z zapisem z UI daje najwyżej ponowne parsowanie: następny odczyt widzi nowy `mtime` i parsuje plik od nowa. Wyjątek: zapis, który nie zmienia ani `mtime`, ani rozmiaru, w tym samym momencie co odczyt w wątku. To akceptujemy jako pomijalne (KISS); nie dodajemy `Lock`.
- **Walidacja przy każdym odczycie to świadomy wybór.** Dziś żadna trasa nie mutuje obiektów z `Storage` (trasy budują nowe obiekty z formularza). Wybieramy bezpieczeństwo przy przyszłych zmianach kosztem kilku ms na walidację. Koszt mierzymy w Unit 3. Cache gotowych modeli zostaje jako follow-up, jeśli pomiar to uzasadni.

## Open Questions

### Resolved During Planning

- Czy pierwsze żądanie po starcie też będzie szybkie? Częściowo. `lifespan` w `main.py` (przez budowę indeksu MIDI) woła `get_songs()` i `get_devices()`, co rozgrzewa cache YAML. Ok. 1,8 s różnicy między pierwszym żądaniem (2,6 s) a kolejnymi (~840 ms) ma jednak inną przyczynę, bo `lifespan` parsuje utwory już dziś. Prawdopodobnie to kompilacja szablonów Jinja albo leniwe importy (hipoteza). Pierwsze żądanie mierzymy osobno w Unit 3, poza celem R7.
- Czy inne moduły czytają YAML bezpośrednio z pominięciem `Storage`? Nie (grep po `src/`).
- Czy potrzebny jest cache między procesami (np. `lp-rc600`)? Nie. `lp-rc600` to osobny proces poza zakresem. Każdy proces z własną instancją `Storage` i tak widzi zmiany przez `mtime`.

### Deferred to Implementation

- Dokładny koszt `model_validate` 14 utworów na i686. Mierzymy po wdrożeniu. Jeśli walidacja okaże się istotna (> ~50 ms), rozważymy cache modeli z kopiowaniem (`model_copy(deep=True)`). To osobna decyzja na podstawie danych.
- Nazwa prywatnej metody i struktury wpisu cache — decyzja implementującego.
- Którą przeglądarkę wybrać. Decyzja po pomiarze w Unit 4. Kandydaci: Firefox po tuningu (bez ryzyka niezgodności) oraz przeglądarki WebKitGTK w kolejności: `surf` (najmniejszy, ma tryb pełnoekranowy, ale bez wbudowanego trybu kiosku), `epiphany --application-mode` (najlepsza zgodność, ale cięższy), `vimb` i `luakit` jako zapas.

## Implementation Units

- [x] **Unit 1: Cache odczytów YAML w `Storage`**

**Goal:** Wszystkie odczyty YAML w `Storage` idą przez cache unieważniany po `(mtime_ns, size)` oraz jawnie przy zapisie i usunięciu.

**Requirements:** R1, R2, R3, R4, R5, R6

**Dependencies:** Brak

**Files:**
- Modify: `packages/paternologia/src/paternologia/storage.py`
- Test: `packages/paternologia/tests/test_storage.py`

**Approach:**
- Dodać w `__init__` pusty słownik cache na instancji.
- Dodać jedną prywatną metodę: `stat()` pliku → porównanie klucza z wpisem → przy trafieniu zwróć dane z cache, przy chybieniu sparsuj, zapisz wpis i zwróć dane. Gdy pliku nie ma, usuń wpis i zgłoś brak tak samo jak dziś (obecne `exists()` w metodach publicznych zostaje).
- Pięć odczytów (`get_devices`, `get_songs_order`, `_load_song_file`, `get_pacer_config`, `get_obs_config`) korzysta z tej metody.
- `save_devices`, `save_songs_order`, `save_song`, `save_pacer_config`, `delete_song` usuwają wpis dla swojej ścieżki po zapisie lub usunięciu.
- `get_songs_order` zwraca kopię listy.
- Zaktualizować nagłówek `ABOUTME`, jeśli opis modułu przestanie być pełny (wzmianka o cache).

**Execution note:** Test-first (TDD według CLAUDE.md). Najpierw testy z licznikiem wywołań parsera, potem implementacja.

**Patterns to follow:**
- Fixture `temp_storage` i styl testów w `tests/test_storage.py`.
- Licznik wywołań parsera: `monkeypatch` na `paternologia.storage.yaml.safe_load` z wrapperem, który liczy wywołania i woła oryginał (to obserwacja prawdziwego parsera, a nie mock danych).

**Test scenarios:**
- Happy path: dwa wywołania `get_songs()` bez zmian na dysku → parser wołany tylko w pierwszym; wynik drugiego równy pierwszemu.
- Happy path: dwa wywołania `get_devices()`, `get_pacer_config()`, `get_obs_config()`, `get_songs_order()` → każdy plik parsowany raz.
- Edge case (R2): zewnętrzny zapis do pliku utworu (zwykłe `write_text` z inną treścią, potem `os.utime` z innym `mtime_ns`) → kolejny `get_song()` zwraca nową treść.
- Edge case (R3): `save_song()` z inną treścią, a potem `os.utime` przywracające stary `mtime_ns` i treść o tym samym rozmiarze → `get_song()` zwraca treść z zapisu (działa jawne unieważnienie).
- Edge case (R3): `save_devices()`, `save_songs_order()`, `save_pacer_config()` → kolejny odczyt zwraca zapisane dane.
- Edge case (R4): `delete_song()` → `get_song()` zwraca `None`, a `get_songs()` nie zawiera usuniętego utworu.
- Edge case (R4): plik utworu usunięty z zewnątrz (`unlink` w teście) → `get_song()` zwraca `None`, `get_songs()` go pomija.
- Edge case (R5): zmiana pola w obiekcie `Song` z `get_song()` (np. nazwy) bez zapisu → kolejny `get_song()` zwraca oryginalną wartość.
- Edge case (R5): `append` do listy z `get_songs_order()` → kolejne wywołanie zwraca listę bez dodanego elementu.
- Edge case: plik pusty lub z samym `{}` → zachowanie jak dziś (`None` dla utworu i pacer config, domyślne `ObsConfig`, pusta lista urządzeń).
- Error path: niepoprawny YAML → wyjątek parsera jak dziś; wpis nie zostaje w cache, więc po poprawie pliku odczyt działa.
- Regresja: wszystkie istniejące testy w `test_storage.py` przechodzą bez zmian.

**Verification:**
- Nowe i istniejące testy w `tests/test_storage.py` są zielone, a wyjście testów jest czyste (bez ostrzeżeń).

- [x] **Unit 2: Testy integracyjne i e2e widoczności zmian przez HTTP**

**Goal:** Potwierdzić przez `TestClient`, że cache nie psuje przepływów UI i że zmiana pliku z zewnątrz jest widoczna w HTML.

**Requirements:** R2, R3, R6

**Dependencies:** Unit 1

**Files:**
- Test: `packages/paternologia/tests/test_api.py`
- Test: `packages/paternologia/tests/test_e2e.py`

**Approach:**
- Użyć istniejących fixture z `Storage` na katalogu tymczasowym i podmianą w `dependencies`.
- Bez zmian w kodzie produkcyjnym. Jeśli test wykaże błąd, poprawka wraca do Unit 1.

**Patterns to follow:**
- Fixture `temp_data_dir` i podmiana storage w `tests/test_e2e.py`.

**Test scenarios:**
- Integration (R2): `GET /` → zewnętrzna zmiana nazwy utworu w pliku YAML (z innym `mtime_ns`) → `GET /` zawiera nową nazwę.
- Integration (R3): edycja utworu przez formularz (POST) → `GET /songs/{id}` pokazuje zmienione dane.
- E2E: przepływ „utwórz utwór → zobacz na liście → usuń → lista bez utworu” działa z cache.
- Integration: przebudowa indeksu MIDI po zapisie utworu (`SongMidiIndex.build` w `routers/songs.py`) widzi nowe dane.

**Verification:**
- Cały katalog `packages/paternologia/tests` jest zielony i bez ostrzeżeń.

- [ ] **Unit 3: Pomiar na lubudu po wdrożeniu**

**Goal:** Potwierdzić R7 na docelowym sprzęcie.

**Requirements:** R7

**Dependencies:** Unit 1, Unit 2, merge do `master` (auto-deploy przez cron)

**Files:** Brak zmian w kodzie.

**Approach:**
- Po auto-deployu powtórzyć pomiar `GET /` (kilka żądań z rozgrzanym serwerem) tak samo jak przy pomiarze bazowym z 2026-11-08 (`wget` na `localhost:8000`, czas w ms).
- Zmierzyć osobno czas `get_songs()` + `get_devices()` przy rozgrzanym cache, aby ocenić koszt `model_validate` (pytanie odłożone wyżej).
- Zmierzyć osobno pierwsze żądanie po restarcie serwera (informacyjnie, poza R7).
- Sprawdzić R2: przy działającym serwerze ręcznie zmienić plik utworu w `data/` → zmiana widoczna w UI bez restartu.

**Verification:**
- `GET /` < 100 ms z rozgrzanym serwerem. Jeśli nie, zapisać wyniki i rozważyć follow-up (cache modeli z kopiowaniem albo `CSafeLoader`).

- [ ] **Unit 4: Pomiar przeglądarek WebKitGTK na lubudu**

**Goal:** Zebrać dane do decyzji o zmianie przeglądarki w kiosku (R8).

**Requirements:** R8

**Dependencies:** Brak. Ten krok jest niezależny od Unit 1–3 i może iść równolegle. Pomiar CPU w spoczynku jest jednak bardziej czytelny po Unit 1, bo serwer nie dokłada wtedy kosztu parsowania.

**Files:** Brak zmian w repo. Zmiany tylko na hoście (instalacja pakietów).

**Approach:**
- Zainstalować `surf` i `epiphany` z repo Void (zgoda użytkownika przed instalacją na hoście).
- Dla każdej przeglądarki (Firefox jako punkt odniesienia): otworzyć `http://localhost:8000` na pełnym ekranie, odczekać do ustabilizowania, zmierzyć sumę RSS wszystkich procesów przeglądarki (z procesami WebKit `WebKitWebProcess` i `WebKitNetworkProcess`) i średnie CPU przez ok. 60 s w spoczynku.
- Pomiar Firefoksa wykonać dwa razy: w obecnej konfiguracji i po tuningu (np. `dom.ipc.processCount=1` w `policies.json` lub w preferencjach profilu). Firefox po tuningu to pełnoprawny kandydat: nie ma ryzyka niezgodności z UI.
- Informacyjnie: ten sam pomiar na stronie live (otwarte SSE) i na liście utworów (bez SSE). Wynik nie wpływa na decyzję w Unit 5. To dane dla osobnego tematu o CPU strony.
- Ręcznie przejść scenariusze z R9 w każdej kandydującej przeglądarce. Zanotować problemy z renderowaniem na GMA 945.
- Wyniki zapisać w sekcji „Wyniki Unit 4” na końcu tego planu. Wniosek (wybrana przeglądarka) dopisać też do pamięci projektu o lubudu.

**Test scenarios:**
- Manual: lista utworów, edycja i zapis utworu przez HTMX → zmiana widoczna bez przeładowania strony.
- Manual: widok live → zdarzenia SSE przychodzą (np. zmiana utworu z Pacera albo z drugiej karty).
- Manual: eksport do Pacera i przycisk nagrywania OBS → akcje wykonują się jak w Firefoksie (OBS jest wyłączony na lubudu, więc sprawdzamy tylko, czy UI zgłasza błąd tak samo).
- Manual: przewijanie i dotyk/klawiatura na ekranie X60s → brak zawieszeń i artefaktów grafiki.

**Verification:**
- Jest tabela: przeglądarka × (RAM, CPU na liście, CPU w live, zgodność R9 tak/nie).

- [ ] **Unit 5: Przełączenie kiosku (warunkowe)**

**Goal:** Kiosk na lubudu startuje w wybranej przeglądarce WebKitGTK (R9).

**Requirements:** R9

**Dependencies:** Unit 4. Wykonujemy tylko wtedy, gdy najlepszy kandydat spełnia R9, zużywa co najmniej ok. 40% mniej RAM niż obecny Firefox, a jego CPU w spoczynku nie jest wyższe niż w obecnym Firefoksie. Kandydatem może być też Firefox po tuningu. Wtedy Unit 5 to tylko zmiana konfiguracji Firefoksa. Jeśli żaden kandydat nie spełnia warunków, zamykamy ten krok z wynikami z Unit 4 i bez zmian.

**Files:**
- Modify (host): `~/.config/autostart/paternologia-kiosk.desktop` na lubudu (albo `policies.json` Firefoksa, jeśli wygra Firefox po tuningu). Launcher zostaje tylko na hoście.

**Approach:**
- Zachować obecny wzorzec: najpierw czekanie na `/health`, potem uruchomienie przeglądarki na pełnym ekranie.
- Sprawdzić, jak wybrana przeglądarka ukrywa paski i kursor oraz blokuje nawigację poza aplikację. Dla `surf` może to wymagać flag pełnego ekranu i wyłączenia skrótów.
- Firefoksa nie usuwać od razu. Zostawić go jako zapasowy skrót na pulpicie przez okres próbny.
- Launcher przetestować w czystym środowisku (zgodnie z wiedzą o autostarcie).

**Test scenarios:**
- Manual / e2e na hoście: restart lubudu → po zalogowaniu kiosk otwiera się sam w nowej przeglądarce na pełnym ekranie.
- Manual: serwer startuje później niż sesja → launcher czeka na `/health` i dopiero potem otwiera stronę.
- Manual: scenariusze z R9 jak w Unit 4.
- Manual: komenda z pliku autostartu uruchomiona pod `env -i` (czyste środowisko jak w autostarcie) otwiera kiosk.

**Verification:**
- Po restarcie hosta kiosk działa w nowej przeglądarce. Pomiar RAM i CPU zgadza się z Unit 4. Pamięć projektu o lubudu ma zaktualizowany opis kiosku.

## System-Wide Impact

- **Interaction graph:** Wszystkie trasy (`routers/songs.py`, `routers/devices.py`, `routers/pacer.py`, `routers/live.py`) oraz `lifespan` w `main.py` korzystają z `Storage`. Zmiana jest przezroczysta dla nich (R6).
- **State lifecycle risks:** Główne ryzyko to stare dane. Pokrywa je klucz `(mtime_ns, size)` plus jawne unieważnienie przy zapisie. Wspólne mutowalne obiekty wyklucza decyzja o cache surowych danych i walidacji przy każdym odczycie.
- **API surface parity:** `lp-rc600` i inne procesy mają własne instancje `Storage` (jeśli w ogóle jej używają). Każda instancja unieważnia cache po `mtime`, więc zachowanie między procesami jest poprawne.
- **Integration coverage:** Unit 2 sprawdza ścieżkę przez HTTP, której testy jednostkowe `Storage` nie pokrywają.

## Risks & Dependencies

- **Ryzyko: zgrubna rozdzielczość `mtime` przy zapisie z zewnątrz.** Gdy zewnętrzny proces dwa razy zapisze plik o tym samym rozmiarze w tym samym takcie zegara, cache może zwrócić starą wersję. To wyjątek opisany w R2. Łagodzenie: zapisy z UI unieważniają cache jawnie, auto-deploy restartuje serwer, a ręczna edycja dwa razy w tym samym takcie zegara jest w praktyce niemożliwa. Ryzyko akceptujemy.
- **Ryzyko: `model_validate` okaże się wolny na i686.** Łagodzenie: pomiar w Unit 3 i odłożona decyzja o cache modeli z kopiowaniem.
- **Zależność:** auto-deploy na lubudu wdraża zmianę po merge do `master`. Do pomiaru w Unit 3 nie trzeba ręcznych kroków.
- **Ryzyko: niezgodność WebKitGTK z UI** (HTMX, SSE, CSS). Łagodzenie: pełny przegląd scenariuszy R9 w Unit 4 przed przełączeniem i Firefox jako zapas.
- **Ryzyko: problemy grafiki na GMA 945** (akceleracja WebKitGTK). Łagodzenie: sprawdzenie w Unit 4. Jeśli są artefakty, wyłączyć akcelerację GPU w WebKitGTK (zmienna środowiskowa) albo odrzucić kandydata.
- **Ryzyko: ucieczka z kiosku.** Lżejsze przeglądarki mogą nie blokować skrótów tak jak polityki Firefoksa. Łagodzenie: sprawdzenie skrótów w Unit 5. Lubudu to sprzęt na scenie w sieci domowej, więc ryzyko jest małe.
- **Zależność:** instalacja pakietów na hoście wymaga zgody użytkownika (zmiana na zewnętrznym hoście).

## Documentation / Operational Notes

- Krótka wzmianka w `packages/paternologia/README.md` (sekcja o danych): edycja plików w `data/` jest widoczna bez restartu, bo `Storage` unieważnia cache po `mtime`.
- Po Unit 3 zaktualizować pamięć projektu o hoście lubudu wynikami pomiaru.

## Wyniki Unit 4

*Do uzupełnienia po pomiarze.*

| Przeglądarka | RAM (suma RSS) | CPU — lista | CPU — live (informacyjnie) | R9 (tak/nie) | Uwagi |
|---|---|---|---|---|---|
| Firefox (obecna konfiguracja) | | | | tak | punkt odniesienia |
| Firefox po tuningu | | | | | |
| surf | | | | | |
| epiphany `--application-mode` | | | | | |

## Sources & References

- Pomiary bazowe na lubudu: rozmowa z 2026-11-08 (`GET /` ~840 ms, parsowanie YAML ~830 ms, brak libyaml).
- Kod: `packages/paternologia/src/paternologia/storage.py`, `dependencies.py`, `main.py` (`lifespan`).
