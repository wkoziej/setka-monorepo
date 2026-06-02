# ABOUTME: Specyfikacja integracji Paternologia z Nektar Pacer
# ABOUTME: Workflow: Paternologia → .syx → amidi/pacer-editor → Pacer

# Specyfikacja: Paternologia → Nektar Pacer

## 1. Koncepcja

Generujemy pliki `.syx` z Paternologii i wgrywamy je do Pacera przez `amidi` (CLI) lub opcjonalnie przez pacer-editor (podgląd/edycja).

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────┐
│   Paternologia  │ ──────▶ │     amidi       │ ──────▶ │ Nektar Pacer│
│   (konfiguracja)│  .syx   │   (terminal)    │  SysEx  │ (hardware)  │
└─────────────────┘         └─────────────────┘         └─────────────┘
                                    │
                            ┌───────┴───────┐
                            │ pacer-editor  │ (opcjonalnie)
                            │ (podgląd/edit)│
                            └───────────────┘
```

### Dlaczego amidi zamiast Web MIDI?

**Web MIDI na Ubuntu nie działa** - Chromium jest wymuszony jako snap, który nie ma dostępu do ALSA MIDI. Błąd: `Platform dependent initialization failed`.

**amidi działa bez problemu:**
```bash
$ amidi -l
Dir Device    Name
IO  hw:7,0,0  RC-600 MIDI 1
IO  hw:8,0,0  PACER MIDI1
IO  hw:8,0,1  PACER MIDI2
```

### Zalety tego podejścia

1. **Działa na Ubuntu** - amidi omija problemy z Web MIDI / snap
2. **Prostota** - jedna komenda wysyła preset do Pacera
3. **Skryptowalność** - można zautomatyzować w bash/Python
4. **pacer-editor opcjonalny** - do podglądu/edycji, nie do wysyłania
5. **Backup/restore** - amidi obsługuje dumpy całego urządzenia

### Wady

1. **Terminal wymagany** - użytkownik musi użyć komendy CLI
2. **Brak wizualnej weryfikacji** - chyba że użyje pacer-editor do podglądu

## 2. Komendy amidi (DZIAŁA!)

**CRITICAL:** Zawsze używaj `--sysex-interval=20` przy wysyłaniu do Pacera!

### 2.1 Podstawowe operacje

```bash
# Lista portów MIDI
amidi -l

# Backup całego Pacera (full dump)
amidi -p hw:8,0,0 -S "F0 00 01 77 7F 02 7F F7" -r backup.syx -t 10

# Wyślij plik .syx do Pacera (CRITICAL: --sysex-interval=20!)
amidi -p hw:8,0,0 --sysex-interval=20 -s preset.syx

# Wyślij surowe bajty hex
amidi -p hw:8,0,0 -S "F0 00 01 77 7F 01 01 00 ... F7"
```

### 2.2 Porty MIDI na tym systemie

| Port | Urządzenie |
|------|------------|
| `hw:7,0,0` | RC-600 MIDI 1 |
| `hw:8,0,0` | PACER MIDI1 |
| `hw:8,0,1` | PACER MIDI2 |

### 2.3 Przykładowy workflow

```bash
# 1. Backup obecnej konfiguracji
amidi -p hw:8,0,0 -S "F0 00 01 77 7F 02 7F F7" -r ~/pacer_backup_$(date +%Y%m%d).syx -t 10

# 2. Eksportuj piosenkę z Paternologii (endpoint do napisania)
curl -o song.syx http://localhost:8000/pacer/export/w-ciszy.syx?preset=A1

# 3. Wyślij do Pacera (CRITICAL: --sysex-interval=20!)
amidi -p hw:8,0,0 --sysex-interval=20 -s song.syx

# 4. (Opcjonalnie) Podgląd w pacer-editor
# Przeciągnij song.syx do http://localhost:3000
```

## 3. Plan implementacji

### Faza 1: Uruchomienie pacer-editor (do podglądu)

#### 3.1 Analiza zależności

```json
// Kluczowe zależności pacer-editor
{
  "react": "^16.6.3",           // Stary, ale powinien działać
  "react-scripts": "2.1.1",     // Może wymagać Node 14-16
  "webmidi": "^2.3.0",          // Web MIDI API wrapper
  "mobx": "^5.15.4"             // State management
}
```

#### 3.2 Kroki uruchomienia (PRZETESTOWANE)

```bash
# 1. Przejdź do katalogu
cd workspace/pacer_programming/pacer-editor

# 2. Zainstaluj zależności
yarn install

# 3. Uruchom dev server (WAŻNE: NODE_OPTIONS dla Node 17+)
NODE_OPTIONS=--openssl-legacy-provider yarn start

# 4. Otwórz http://localhost:3000
# UWAGA: Web MIDI nie działa na Ubuntu (snap), ale można:
#   - Przeciągać pliki .syx do podglądu/edycji
#   - Eksportować edytowane pliki
```

#### 3.3 Potencjalne problemy i rozwiązania

| Problem | Rozwiązanie |
|---------|-------------|
| `ERR_OSSL_EVP_UNSUPPORTED` | Dodaj `NODE_OPTIONS=--openssl-legacy-provider` |
| Web MIDI nie działa | To normalne na Ubuntu/snap - użyj amidi |
| Stare ostrzeżenia ESLint | Ignoruj - aplikacja działa |

#### 3.4 Użycie pacer-editor do podglądu

1. Uruchom: `NODE_OPTIONS=--openssl-legacy-provider yarn start`
2. Otwórz `http://localhost:3000`
3. Przeciągnij plik `.syx` do okna (np. `pacer_current_dump.syx`)
4. Przeglądaj/edytuj konfigurację wizualnie
5. Eksportuj zmodyfikowany `.syx` i wyślij przez `amidi`

### Faza 2: Eksport z Paternologii do .syx

#### 3.5 Generator plików SysEx

Wykorzystamy kod z pierwszej specyfikacji do generowania plików .syx:

```python
# src/paternologia/pacer/export.py

from .sysex import PacerSysExBuilder
from ..models import Song

def export_song_to_syx(song: Song, target_preset: str = "A1") -> bytes:
    """Eksportuj piosenkę do pliku .syx gotowego do załadowania w pacer-editor"""

    preset_index = preset_name_to_index(target_preset)
    builder = PacerSysExBuilder(preset_index)
    messages = []

    # Nazwa presetu
    preset_name = song.song.name[:7]
    messages.append(builder.build_preset_name(preset_name))

    # Przyciski
    for btn_idx, button in enumerate(song.pacer[:6]):
        control_id = 0x0D + btn_idx  # SW1-SW6

        for step_idx, action in enumerate(button.actions[:6], start=1):
            messages.append(builder.build_control_step(
                control_id=control_id,
                step_index=step_idx,
                channel=get_device_channel(action.device),
                msg_type=action_type_to_midi(action.type),
                data1=get_data1(action),
                data2=get_data2(action),
                data3=0,
                active=True
            ))

        # LED dla pierwszego kroku
        messages.append(builder.build_control_led(
            control_id=control_id,
            step_index=1,
            midi_ctrl=0,
            active_color=0x0D,  # Green
            inactive_color=0x00
        ))

        # Control mode: all steps
        messages.append(builder.build_control_mode(control_id, 0))

    return b"".join(messages)
```

#### 3.6 Endpoint API

```python
# src/paternologia/routers/pacer.py

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(prefix="/pacer", tags=["pacer"])

@router.get("/export/{song_id}.syx")
def export_syx(song_id: str, preset: str = "A1"):
    """Eksportuj piosenkę do pliku .syx"""
    song = storage.get_song(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    syx_data = export_song_to_syx(song, preset)

    return Response(
        content=syx_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{song_id}_{preset}.syx"'
        }
    )
```

### Faza 3: Integracja UI

#### 3.7 Opcja A: Osobne aplikacje (najprostsza)

```html
<!-- templates/song_detail.html -->
<div class="pacer-section">
    <h3>Export to Pacer</h3>

    <label>Target Preset:</label>
    <select id="preset-select">
        <option value="A1">A1</option>
        <!-- ... -->
    </select>

    <a id="download-syx"
       href="/pacer/export/{{ song.song.id }}.syx?preset=A1"
       download>
        Download .syx file
    </a>

    <p class="hint">
        Open the .syx file in
        <a href="http://localhost:3000" target="_blank">Pacer Editor</a>
        and click "Send to Pacer"
    </p>
</div>

<script>
document.getElementById('preset-select').addEventListener('change', (e) => {
    const link = document.getElementById('download-syx');
    link.href = `/pacer/export/{{ song.song.id }}.syx?preset=${e.target.value}`;
});
</script>
```

#### 3.8 Opcja B: Embedded iframe (średnia złożoność)

```html
<!-- Osadź pacer-editor w iframe -->
<iframe
    src="http://localhost:3000"
    width="100%"
    height="600px"
    allow="midi">
</iframe>
```

**Problem**: Drag & drop pliku .syx do iframe może nie działać.

#### 3.9 Opcja C: Wspólny backend (zaawansowana)

Dodanie API do pacer-editor, które przyjmuje dane z Paternologii:

```javascript
// Dodać do pacer-editor/src/App.js lub nowy endpoint

// Nasłuchuj na wiadomości z parent window (Paternologia)
window.addEventListener('message', async (event) => {
    if (event.data.type === 'LOAD_SYSEX') {
        const sysexData = new Uint8Array(event.data.sysex);
        await state.readFiles([new Blob([sysexData])]);
    }
});
```

```html
<!-- W Paternologii -->
<iframe id="pacer-editor" src="http://localhost:3000"></iframe>

<script>
async function sendToPacerEditor(songId, preset) {
    const response = await fetch(`/pacer/export/${songId}.syx?preset=${preset}`);
    const sysex = await response.arrayBuffer();

    document.getElementById('pacer-editor')
        .contentWindow.postMessage({
            type: 'LOAD_SYSEX',
            sysex: Array.from(new Uint8Array(sysex))
        }, '*');
}
</script>
```

### Faza 4: Modernizacja pacer-editor (opcjonalna)

Jeśli stare zależności powodują problemy:

#### 3.10 Aktualizacja React

```bash
cd pacer-editor

# Backup
cp package.json package.json.backup

# Aktualizacja kluczowych zależności
npm install react@18 react-dom@18 react-scripts@5
npm install mobx@6 mobx-react@9

# Napraw breaking changes w kodzie
# - MobX 6: makeAutoObservable zamiast decorate
# - React 18: createRoot zamiast ReactDOM.render
```

#### 3.11 Migracja do Vite (alternatywa)

```bash
# Szybsza alternatywa dla react-scripts
npm create vite@latest pacer-editor-modern -- --template react
# Przenieś src/ do nowego projektu
```

## 4. Workflow użytkownika

### Scenariusz: Konfiguracja piosenki na Pacerze

```
1. [Paternologia] Użytkownik tworzy/edytuje piosenkę
   - Definiuje przyciski i akcje MIDI

2. [Paternologia] Klika "Export to Pacer"
   - Wybiera preset docelowy (np. B3)
   - Pobiera plik .syx

3. [Terminal] Wysyła do Pacera przez amidi:
   amidi -p hw:8,0,0 --sysex-interval=20 -s song_B3.syx

4. [Opcjonalnie] Podgląd w pacer-editor:
   - Przeciąga .syx do http://localhost:3000
   - Weryfikuje konfigurację wizualnie

5. [Pacer] Użytkownik może używać presetu bez komputera
```

### Scenariusz: Backup i restore

```bash
# Backup
amidi -p hw:8,0,0 -S "F0 00 01 77 7F 02 7F F7" -r ~/pacer_backup.syx -t 10

# Restore (CRITICAL: --sysex-interval=20!)
amidi -p hw:8,0,0 --sysex-interval=20 -s ~/pacer_backup.syx
```

## 5. Struktura plików

```
paternologia/
├── src/paternologia/
│   ├── pacer/
│   │   ├── __init__.py
│   │   ├── sysex.py          # Generator wiadomości SysEx
│   │   ├── export.py         # Eksport Song → .syx
│   │   └── constants.py      # Stałe protokołu Pacer
│   └── routers/
│       └── pacer.py          # Endpoint /pacer/export
├── templates/
│   └── partials/
│       └── pacer_export.html # UI eksportu
└── workspace/
    └── pacer_programming/
        └── pacer-editor/     # Sklonowane repo (do uruchomienia)
```

## 6. Minimalna implementacja (MVP)

### Co zrobić od razu:

1. **Uruchomić pacer-editor** (1-2h)
   - `yarn install && yarn start`
   - Rozwiązać ewentualne problemy z zależnościami

2. **Napisać generator .syx** (2-3h)
   - Plik `src/paternologia/pacer/sysex.py`
   - Podstawowe typy: Program Change, CC

3. **Dodać endpoint eksportu** (1h)
   - GET `/pacer/export/{song_id}.syx`

4. **Dodać link w UI** (30min)
   - Przycisk "Download .syx" na stronie piosenki

### Co zostawić na później:

- Embedded iframe z pacer-editor
- Automatyczna synchronizacja
- Konfiguracja kanałów MIDI per urządzenie
- Kolorystyka LED

## 7. Testowanie

### Test manualny workflow:

```bash
# 1. Uruchom pacer-editor
cd workspace/pacer_programming/pacer-editor
yarn start

# 2. Uruchom Paternologia
cd ../..
uv run fastapi dev src/paternologia/main.py

# 3. Utwórz piosenkę w Paternologii
# 4. Pobierz .syx
# 5. Otwórz pacer-editor, załaduj .syx
# 6. Podłącz Pacer, wyślij dane
```

### Test jednostkowy generatora SysEx:

```python
# tests/test_pacer_sysex.py

def test_preset_name_sysex():
    builder = PacerSysExBuilder(preset_index=0x07)  # B1
    sysex = builder.build_preset_name("TEST")

    assert sysex[0] == 0xF0  # Start
    assert sysex[-1] == 0xF7  # End
    assert sysex[1:4] == bytes([0x00, 0x01, 0x77])  # Manufacturer

def test_control_step_sysex():
    builder = PacerSysExBuilder(preset_index=0x00)  # A1
    sysex = builder.build_control_step(
        control_id=0x0D,  # SW1
        step_index=1,
        channel=0,
        msg_type=0x45,  # Program & Bank
        data1=5,        # Program 5
        data2=0,
        data3=0,
        active=True
    )

    # Weryfikuj strukturę
    assert len(sysex) > 10
    assert sysex[5] == 0x01  # CMD_SET
    assert sysex[6] == 0x01  # TARGET_PRESET
```

## 8. Porównanie podejść

| Aspekt | Spec 1 (python-rtmidi) | Spec 2 (amidi + pacer-editor) |
|--------|------------------------|-------------------------------|
| Działa na Ubuntu | ❓ Wymaga testów | ✅ Przetestowane |
| Czas implementacji | 2-3 tygodnie | 1 tydzień |
| Zależności | python-rtmidi | amidi (apt), yarn (opcja) |
| UX | Zintegrowany | Terminal + opcjonalny podgląd |
| Maintenance | Więcej kodu | Mniej kodu, sprawdzone narzędzia |
| Backup/restore | Do napisania | ✅ amidi obsługuje |

## 9. Rekomendacja

**Użyj Spec 2 (amidi)** - działa od razu:

1. ✅ **amidi działa** - przetestowane na tym systemie
2. ✅ **pacer-editor działa** - do podglądu/edycji (opcjonalnie)
3. 🔨 **Do napisania**: generator .syx w Paternologii

### Następne kroki:

1. Napisz generator `.syx` w Paternologii (~200 linii Python)
2. Dodaj endpoint `GET /pacer/export/{song_id}.syx`
3. Dodaj przycisk w UI + instrukcję `amidi -p hw:8,0,0 --sysex-interval=20 -s ...`

## 10. Źródła i pliki

### Lokalne pliki
- `workspace/pacer_programming/pacer_current_dump.syx` - backup Twojego Pacera
- `workspace/pacer_programming/pacer-editor/` - edytor (do podglądu)
- `workspace/pacer_programming/pacer-editor/src/pacer/sysex.js` - parser SysEx

### Dokumentacja
- `workspace/pacer_programming/README.md` - streszczenie techniczne
- `workspace/pacer_programming/SPEC_PACER_PROGRAMMING.md` - alternatywna spec (python-rtmidi)
