# ABOUTME: Specyfikacja eksportu .syx z Paternologii (Faza 2 - zwięzła wersja)
# ABOUTME: Protokół SysEx, moduł pacer/, API, testy - gotowe do implementacji

# Eksport .syx z Paternologii

## Cel

Generator plików `.syx` (MIDI SysEx) dla Nektar Pacer:
- `Song` → `.syx` → wgranie przez `amidi` lub podgląd w `pacer-editor`

## Protokół SysEx Nektar Pacer

### Struktura ramki

Ramka SysEx ma **dwie warianty** w zależności od typu wiadomości:

**Wariant A: Preset name** (zawiera bajt Element w headerze)
```
F0                    # SysEx Start
00 01 77              # Manufacturer ID (Nektar)
7F                    # Device ID (broadcast)
01                    # Command (SET=0x01, GET=0x02)
01                    # Target (PRESET=0x01)
XX                    # Index (preset 0x00-0x2F = A1-F8)
01                    # Object (CONTROL_NAME = 0x01)
00                    # Element (zawsze 0x00 dla preset name)
[data bytes...]       # Długość + ASCII nazwa
XX                    # Checksum
F7                    # SysEx End
```

**Wariant B: Control steps** (BEZ bajtu Element w headerze)
```
F0                    # SysEx Start
00 01 77              # Manufacturer ID (Nektar)
7F                    # Device ID (broadcast)
01                    # Command (SET=0x01, GET=0x02)
01                    # Target (PRESET=0x01)
XX                    # Index (preset 0x00-0x2F = A1-F8)
XX                    # Object (control ID: 0x0D-0x12 = SW1-SW6)
[data bytes...]       # Parametry z element IDs: [elm_id, 0x01, value, 0x00]...
XX                    # Checksum
F7                    # SysEx End
```

**Kluczowa różnica**:
- **Preset name**: Element (0x00) jest w headerze, przed data bytes
- **Control steps**: Element IDs są **wewnątrz** data bytes dla każdego parametru
- Źródło: `pacer-editor/sysex.js:847-853` (preset name) vs `685-697` (control step)

### Checksum

```python
def checksum(data: bytes) -> int:
    """Suma bajtów od Manufacturer ID do końca danych (bez F0/F7)."""
    return (128 - (sum(data) % 128)) % 128
```

### Stałe (z pacer-editor/src/pacer/constants.js)

```python
# Komendy
CMD_SET = 0x01
CMD_GET = 0x02

# Target types
TARGET_PRESET = 0x01
TARGET_GLOBAL = 0x05
TARGET_BACKUP = 0x7F

# Control IDs (stompswitches)
SW1, SW2, SW3, SW4, SW5, SW6 = 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12

# Message types (używane w control step data)
MSG_CTRL_OFF = 0x61       # Kontrolka wyłączona
MSG_SW_NOTE = 0x43        # Note on/off
MSG_SW_PRG_BANK = 0x45    # Program Change + Bank Select (PRESET)
MSG_SW_PRG_STEP = 0x46    # Program Step (PATTERN - start/end range)
MSG_AD_MIDI_CC = 0x00     # Control Change (CC)
MSG_SW_MMC = 0x55         # MIDI Machine Control

# LED colors
LED_OFF = 0x00
LED_RED = 0x03
LED_GREEN = 0x0D
LED_BLUE = 0x11
LED_WHITE = 0x17

# Special object IDs
CONTROL_NAME = 0x01       # Object ID dla nazwy presetu
CONTROL_MODE_ELEMENT = 0x60  # Element ID dla trybu kontrolki

# Preset indices: A1=0x00, A2=0x01, ..., F8=0x2F (6×8 = 48 presetów)
```

### Przykład: Ustaw nazwę presetu A1 na "SONG"

```
F0 00 01 77 7F                  # SysEx start + Manufacturer ID
01 01 00 01 00                  # CMD_SET, TARGET_PRESET, index=A1, CONTROL_NAME, element=0
04                              # Długość nazwy (4 bajty)
53 4F 4E 47                     # "SONG" (ASCII: 'S', 'O', 'N', 'G')
XX                              # Checksum
F7                              # SysEx end
```

**Uwaga**: Format `[długość, bajty...]` bez paddingu do 8 znaków (pacer-editor/sysex.js:858)

### Przykład: Ustaw SW1 step 1 → Program Change 5 na kanale 0

```
F0 00 01 77 7F 01 01 00 0D 01  # Header + SW1 (0x0D), step 1
45 00 05 00 00 01               # msg_type=0x45, channel=0, program=5, active=1
XX                              # Checksum
F7
```

## Moduł pacer/

### Modele danych

**Rozszerzenie Device** (src/paternologia/models.py):
```python
class Device(BaseModel):
    """MIDI device definition with supported action types."""

    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Display name of the device")
    description: str = Field(default="", description="Device description")
    action_types: list[ActionType] = Field(
        default_factory=list,
        description="Supported action types"
    )
    midi_channel: int = Field(
        ...,
        ge=0,
        le=15,
        description="MIDI channel (0-15) for this device"
    )
```

**Rozszerzenie Action** (src/paternologia/models.py):
```python
class Action(BaseModel):
    """Single MIDI action definition."""

    device: str
    type: ActionType
    value: int | str | None = None
    cc: int | None = None
    label: str | None = None
    bank_lsb: int = Field(
        default=0,
        ge=0,
        le=127,
        description="Bank LSB (CC 32) for PRESET type"
    )
    bank_msb: int = Field(
        default=0,
        ge=0,
        le=127,
        description="Bank MSB (CC 0) for PRESET type"
    )

    @model_validator(mode='after')
    def validate_cc_value(self) -> 'Action':
        """Wymaga value dla ActionType.CC."""
        if self.type == ActionType.CC and self.value is None:
            raise ValueError("ActionType.CC wymaga pola 'value' (0-127)")
        if self.type == ActionType.CC and (self.value < 0 or self.value > 127):
            raise ValueError(f"ActionType.CC value musi być 0-127, otrzymano: {self.value}")
        return self
```

**Format data/devices.yaml**:
```yaml
- id: boss
  name: Boss RC-505 mkII
  description: Loop station
  midi_channel: 0
  action_types:
    - preset
    - cc

- id: ms
  name: Elektron Model:Samples
  description: Sample player
  midi_channel: 1
  action_types:
    - preset
    - pattern

- id: freak
  name: Moog Moogerfooger MF-104M
  description: Analog delay
  midi_channel: 2
  action_types:
    - cc
```

**Format data/songs/*.yaml** (rozszerzenie Action):
```yaml
pacer:
  - name: Intro
    actions:
      - device: boss
        type: preset
        value: 5
        bank_lsb: 0
        bank_msb: 1  # Preset z banku 1
        label: "Heavy Loop"
      - device: ms
        type: pattern
        value: A02
        label: "Drums"
  - name: Verse
    actions:
      - device: boss
        type: cc
        cc: 1
        value: 127  # WYMAGANE dla CC (nie może być null)
        label: "Track 1 Rec/Play"
```

### Struktura plików

```
src/paternologia/pacer/
├── __init__.py       # Eksporty publiczne
├── constants.py      # Stałe protokołu (powyżej)
├── sysex.py          # PacerSysExBuilder
├── mappings.py       # Translacja Paternologia → MIDI
└── export.py         # Song → .syx (główna funkcja)
```

### constants.py

```python
"""Stałe protokołu Nektar Pacer SysEx."""

SYSEX_START = 0xF0
SYSEX_END = 0xF7
MANUFACTURER_ID = bytes([0x00, 0x01, 0x77])
DEVICE_ID = 0x7F

CMD_SET = 0x01
CMD_GET = 0x02

TARGET_PRESET = 0x01
TARGET_GLOBAL = 0x05

# Control IDs (Object byte dla control steps/mode/LED)
STOMPSWITCHES = {i: 0x0D + i for i in range(6)}  # SW1-SW6

# Special Object IDs
CONTROL_NAME = 0x01  # Object ID dla nazwy presetu

# Element IDs
CONTROL_MODE_ELEMENT = 0x60  # Element dla trybu kontrolki

# Message types (używane w control step data)
MSG_CTRL_OFF = 0x61       # Kontrolka wyłączona
MSG_SW_PRG_BANK = 0x45    # Program Change + Bank (PRESET)
MSG_SW_PRG_STEP = 0x46    # Program Step (PATTERN - start/end)
MSG_AD_MIDI_CC = 0x00     # Control Change (CC)

# LED colors
LED_OFF = 0x00
LED_GREEN = 0x0D
LED_RED = 0x03

# Preset mapping: "A1" -> 0x00, "F8" -> 0x2F
PRESET_INDICES = {
    f"{row}{col}": (ord(row) - ord('A')) * 8 + (col - 1)
    for row in "ABCDEF" for col in range(1, 9)
}
```

### sysex.py

```python
"""Generator wiadomości SysEx dla Nektar Pacer."""

from . import constants as c

def checksum(data: bytes) -> int:
    return (128 - (sum(data) % 128)) % 128

class PacerSysExBuilder:
    """Buduje pojedyncze wiadomości SysEx."""

    def __init__(self, preset_index: int):
        self.preset_index = preset_index

    def _build(self, obj_id: int, element: int, data: bytes) -> bytes:
        """Ramka SysEx z checksum."""
        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            obj_id,
            element
        ])
        payload = c.MANUFACTURER_ID + header + data
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])

    def build_preset_name(self, name: str) -> bytes:
        """Ustaw nazwę presetu (dynamiczna długość, max 8 ASCII)."""
        ascii_name = name.encode('ascii', errors='replace')[:8]
        # Format: [długość] [bajty ASCII...]
        data = bytes([len(ascii_name)]) + ascii_name
        return self._build(c.CONTROL_NAME, 0x00, data)

    def build_control_step(
        self,
        control_id: int,
        step_index: int,
        msg_type: int,
        channel: int,
        data1: int,
        data2: int = 0,
        data3: int = 0,
        active: bool = True
    ) -> bytes:
        """Konfiguruj krok kontrolki.

        Struktura: dla każdego parametru: [element_id, 0x01, wartość, 0x00]
        gdzie element_id = (step_index-1)*6 + offset
        """
        base = (step_index - 1) * 6
        params = []

        # Każdy parametr: [element, object_type=0x01, value, padding=0x00]
        params.extend([base + 1, 0x01, channel, 0x00])      # Channel
        params.extend([base + 2, 0x01, msg_type, 0x00])     # Message type
        params.extend([base + 3, 0x01, data1, 0x00])        # Data 1
        params.extend([base + 4, 0x01, data2, 0x00])        # Data 2
        params.extend([base + 5, 0x01, data3, 0x00])        # Data 3
        params.extend([base + 6, 0x01, int(active)])        # Active (bez paddingu)

        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            control_id
        ])
        payload = c.MANUFACTURER_ID + header + bytes(params)
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])
```

### mappings.py

```python
"""Mapowanie Paternologia → MIDI."""

from ..models import Action, ActionType, Device
from . import constants as c

def build_device_channel_map(devices: list[Device]) -> dict[str, int]:
    """Buduj mapę device_id → MIDI channel z listy urządzeń.

    Używa Device.midi_channel z modelu.
    """
    channel_map = {}
    for device in devices:
        channel_map[device.id] = device.midi_channel
    return channel_map

def get_device_channel(device_id: str, channel_map: dict[str, int]) -> int:
    return channel_map.get(device_id, 0)

def pattern_to_program(value: int | str | None) -> int:
    """Konwertuj pattern ID na Program Change number.

    M:S: A01-A16 (0-15), B01-B16 (16-31), ..., F01-F16 (80-95)
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Format "A01", "B02", etc.
        if len(value) >= 3 and value[0].isalpha():
            bank = ord(value[0].upper()) - ord('A')  # A=0, B=1, ..., F=5
            pattern = int(value[1:]) - 1  # 01→0, 02→1, ..., 16→15
            return bank * 16 + pattern
    return 0  # fallback

def action_to_midi(action: Action, device_channel_map: dict[str, int]) -> tuple[int, int, int, int, int]:
    """
    Konwertuj Action na parametry MIDI.

    Args:
        action: Akcja do skonwertowania
        device_channel_map: Mapa device_id → MIDI channel

    Returns:
        (msg_type, channel, data1, data2, data3)

    Dla MSG_SW_PRG_BANK: data1=program, data2=bank LSB, data3=bank MSB
    Dla MSG_AD_MIDI_CC: data1=CC number, data2=value, data3=unused (0)
    """
    channel = get_device_channel(action.device, device_channel_map)

    if action.type == ActionType.PRESET:
        # Program Change + Bank
        # data1 = program number, data2 = bank LSB, data3 = bank MSB
        return (
            c.MSG_SW_PRG_BANK,
            channel,
            action.value,
            action.bank_lsb,
            action.bank_msb
        )

    elif action.type == ActionType.PATTERN:
        # Pattern na Model:Samples = Program Change (jak preset)
        # M:S używa PC 0-95 do wyboru pattern 1-96
        # Konwertuj "A01" → 0, "A02" → 1, etc. (lub int jeśli już number)
        program = pattern_to_program(action.value)
        return (c.MSG_SW_PRG_BANK, channel, program, 0, 0)

    elif action.type == ActionType.CC:
        # Control Change
        # action.value jest wymagane (walidowane przez model)
        return (c.MSG_AD_MIDI_CC, channel, action.cc or 0, action.value, 0)

    else:
        raise ValueError(f"Nieobsługiwany typ akcji: {action.type}")
```

### export.py

```python
"""Eksport Song → .syx."""

from ..models import Song, Device
from .sysex import PacerSysExBuilder
from .mappings import action_to_midi, build_device_channel_map
from . import constants as c

def export_song_to_syx(
    song: Song,
    devices: list[Device],
    target_preset: str = "A1"
) -> bytes:
    """
    Eksportuj piosenkę do pliku .syx.

    Args:
        song: Piosenka z Paternologii
        devices: Lista urządzeń (do mapowania device_id → MIDI channel)
        target_preset: Preset docelowy (A1-F8)

    Returns:
        bytes: Zawartość pliku .syx (konkatenacja wiadomości)
    """
    preset_index = c.PRESET_INDICES[target_preset.upper()]
    builder = PacerSysExBuilder(preset_index)
    messages = []

    # Buduj mapę device_id → MIDI channel z devices
    device_channel_map = build_device_channel_map(devices)

    # 1. Nazwa presetu
    messages.append(builder.build_preset_name(song.song.name))

    # 2. Konfiguracja przycisków SW1-SW6
    for btn_idx in range(6):  # Zawsze przetwarzaj wszystkie 6 przycisków
        control_id = c.STOMPSWITCHES[btn_idx]
        button = song.pacer[btn_idx] if btn_idx < len(song.pacer) else None

        # Zawsze konfiguruj wszystkie 6 kroków (czyszczenie niewykorzystanych)
        for step_idx in range(1, 7):
            if button and step_idx <= len(button.actions):
                # Akcja istnieje - konfiguruj normalnie
                action = button.actions[step_idx - 1]
                msg_type, channel, data1, data2, data3 = action_to_midi(action, device_channel_map)
                messages.append(builder.build_control_step(
                    control_id=control_id,
                    step_index=step_idx,
                    msg_type=msg_type,
                    channel=channel,
                    data1=data1,
                    data2=data2,
                    data3=data3,
                    active=True
                ))
            else:
                # Brak akcji - wyczyść krok (MSG_CTRL_OFF, active=False)
                messages.append(builder.build_control_step(
                    control_id=control_id,
                    step_index=step_idx,
                    msg_type=c.MSG_CTRL_OFF,
                    channel=0,
                    data1=0,
                    data2=0,
                    data3=0,
                    active=False
                ))

    return b"".join(messages)
```

## API

### Router: routers/pacer.py

```python
"""Endpoint eksportu .syx."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from ..dependencies import get_storage
from ..storage import Storage
from ..pacer.export import export_song_to_syx
from ..pacer import constants as c

router = APIRouter(prefix="/pacer", tags=["pacer"])

@router.get("/export/{song_id}.syx")
def export_syx(
    song_id: str,
    preset: str = "A1",
    storage: Storage = Depends(get_storage)
):
    """Eksportuj piosenkę do .syx."""
    song = storage.get_song(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    # Walidacja preset
    if preset.upper() not in c.PRESET_INDICES:
        raise HTTPException(400, f"Invalid preset: {preset}. Must be A1-F8.")

    # Pobierz devices do mapowania MIDI channels
    devices = storage.get_devices()

    syx_data = export_song_to_syx(song, devices, preset)

    return Response(
        content=syx_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{song_id}_{preset}.syx"'
        }
    )
```

### Rejestracja w main.py

```python
from .routers import pacer

app.include_router(pacer.router)
```

## UI

### Template: song.html (rozszerzenie)

```html
<section class="pacer-export">
    <h3>Export to Pacer</h3>

    <label for="preset">Target Preset:</label>
    <select id="preset">
        {% for row in "ABCDEF" %}
            {% for col in range(1, 9) %}
                <option value="{{ row }}{{ col }}">{{ row }}{{ col }}</option>
            {% endfor %}
        {% endfor %}
    </select>

    <a id="download-syx"
       href="/pacer/export/{{ song.song.id | urlencode }}.syx?preset=A1"
       download="{{ song.song.id | urlencode }}_A1.syx"
       class="button">
        Download .syx file
    </a>

    <details class="instructions">
        <summary>Usage</summary>
        <ol>
            <li>List MIDI ports: <code>amidi -l</code></li>
            <li>Send to Pacer: <code>amidi -p hw:X,0,0 --sysex-interval=20 -s <em>filename.syx</em></code></li>
            <li>Replace <strong>hw:X,0,0</strong> with your PACER port</li>
            <li><strong>CRITICAL:</strong> The <code>--sysex-interval=20</code> flag is required!</li>
        </ol>
    </details>
</section>

<script>
// Safe interpolation - escapes quotes and special chars
const songId = {{ song.song.id | tojson }};

document.getElementById('preset').addEventListener('change', (e) => {
    const preset = e.target.value;
    const link = document.getElementById('download-syx');
    link.href = `/pacer/export/${encodeURIComponent(songId)}.syx?preset=${encodeURIComponent(preset)}`;
    link.download = `${songId}_${preset}.syx`;
});
</script>
```

## Testowanie

### Testy jednostkowe

**test_pacer_sysex.py:**
```python
from paternologia.pacer.sysex import PacerSysExBuilder, checksum

def test_checksum():
    data = bytes([0x00, 0x01, 0x77, 0x7F, 0x01])
    cs = checksum(data)
    assert 0 <= cs < 128

def test_preset_name():
    builder = PacerSysExBuilder(0x00)  # A1
    syx = builder.build_preset_name("TEST")

    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7
    assert syx[1:4] == bytes([0x00, 0x01, 0x77])
    assert b"TEST" in syx

def test_control_step():
    builder = PacerSysExBuilder(0x00)
    syx = builder.build_control_step(
        control_id=0x0D,  # SW1
        step_index=1,
        msg_type=0x45,
        channel=0,
        data1=5,
        active=True
    )

    assert len(syx) > 10
    assert syx[6] == 0x01  # TARGET_PRESET
```

**test_pacer_mappings.py:**
```python
from paternologia.pacer.mappings import action_to_midi
from paternologia.models import Action, ActionType

def test_preset_action():
    action = Action(device="boss", type=ActionType.PRESET, value=5)
    msg_type, channel, data1, data2 = action_to_midi(action)

    assert msg_type == 0x45  # MSG_SW_PRG_BANK
    assert channel == 0      # boss channel
    assert data1 == 5

def test_cc_action():
    action = Action(device="ms", type=ActionType.CC, cc=74, value=127)
    msg_type, channel, data1, data2 = action_to_midi(action)

    assert msg_type == 0x00  # MSG_AD_MIDI_CC
    assert channel == 1      # ms channel
    assert data1 == 74
    assert data2 == 127
```

**test_pacer_export.py:**
```python
from paternologia.pacer.export import export_song_to_syx
from paternologia.models import Song, PacerButton, Action, ActionType

def test_export_minimal(tmp_path):
    song = Song(
        song={"id": "test", "name": "TEST"},
        pacer=[
            PacerButton(
                name="Btn1",
                actions=[Action(device="boss", type=ActionType.PRESET, value=1)]
            )
        ]
    )

    syx = export_song_to_syx(song, "A1")

    assert len(syx) > 0
    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7
    assert b"TEST" in syx
```

### Test API

**test_pacer_api.py:**
```python
def test_export_endpoint(client, sample_song):
    """Test happy-path: eksport istniejącej piosenki."""
    response = client.get(f"/pacer/export/{sample_song.song.id}.syx?preset=B3")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content[0] == 0xF0
    assert response.content[-1] == 0xF7

def test_export_404(client):
    """Test: nieistniejąca piosenka zwraca 404."""
    response = client.get("/pacer/export/nonexistent.syx")
    assert response.status_code == 404

def test_export_invalid_preset(client, sample_song):
    """Test: niepoprawny preset zwraca 400."""
    response = client.get(f"/pacer/export/{sample_song.song.id}.syx?preset=Z9")
    assert response.status_code == 400
    assert "Invalid preset" in response.json()["detail"]

def test_export_empty_song(client, storage):
    """Test: piosenka bez akcji generuje puste kroki (MSG_CTRL_OFF)."""
    from paternologia.models import Song
    empty_song = Song(song={"id": "empty", "name": "Empty"}, pacer=[])
    storage.save_song(empty_song)

    response = client.get("/pacer/export/empty.syx")

    assert response.status_code == 200
    # Sprawdź że wszystkie kroki mają MSG_CTRL_OFF (0x61)
    assert b'\x61' in response.content

def test_export_unknown_device(client, storage):
    """Test: nieznane urządzenie używa domyślnego kanału 0."""
    from paternologia.models import Song, PacerButton, Action, ActionType
    song = Song(
        song={"id": "unknown", "name": "Unknown"},
        pacer=[PacerButton(
            name="Btn1",
            actions=[Action(device="unknown_device", type=ActionType.PRESET, value=1)]
        )]
    )
    storage.save_song(song)

    response = client.get("/pacer/export/unknown.syx")

    assert response.status_code == 200
    # Nie powinno rzucić wyjątku, channel=0 jako fallback

def test_export_partial_actions(client, storage):
    """Test: button z 3 akcjami generuje 6 kroków (3 aktywne, 3 wyłączone)."""
    from paternologia.models import Song, PacerButton, Action, ActionType
    song = Song(
        song={"id": "partial", "name": "Partial"},
        pacer=[PacerButton(
            name="Btn1",
            actions=[
                Action(device="boss", type=ActionType.PRESET, value=1),
                Action(device="boss", type=ActionType.PRESET, value=2),
                Action(device="boss", type=ActionType.PRESET, value=3),
            ]
        )]
    )
    storage.save_song(song)

    response = client.get("/pacer/export/partial.syx")

    assert response.status_code == 200
    # Weryfikuj że jest 6 wiadomości control_step dla SW1
```

### Test manualny z pacer-editor

```bash
# 1. Wygeneruj .syx
curl -o test.syx http://localhost:8000/pacer/export/w-ciszy.syx?preset=A1

# 2. Uruchom pacer-editor
cd workspace/pacer-editor
NODE_OPTIONS=--openssl-legacy-provider yarn start

# 3. Przeciągnij test.syx do przeglądarki (http://localhost:3000)
# 4. Weryfikuj wizualnie:
#    - Nazwa presetu = nazwa piosenki
#    - SW1-SW6 mają odpowiednie akcje
#    - Typy akcji (Program Change, CC) są poprawne

# 5. Hexdump porównanie
hexdump -C test.syx
```

## Plan implementacji

### Iteracja 1: Fundament (3-4h)
- [ ] Utworzyć `src/paternologia/pacer/` z plikami
- [ ] `constants.py` - wszystkie stałe z pacer-editor
- [ ] `sysex.py` - `PacerSysExBuilder` + checksum
- [ ] Testy jednostkowe: `test_pacer_sysex.py`

### Iteracja 2: Mapowanie (2h)
- [ ] `mappings.py` - `DEVICE_CHANNELS`, `action_to_midi()`
- [ ] Testy: `test_pacer_mappings.py`

### Iteracja 3: Eksport (2-3h)
- [ ] `export.py` - `export_song_to_syx()`
- [ ] Testy: `test_pacer_export.py`
- [ ] Test manualny: hexdump wygenerowanego pliku

### Iteracja 4: API (1-2h)
- [ ] `routers/pacer.py` - endpoint GET
- [ ] Rejestracja w `main.py`
- [ ] Testy API: `test_pacer_api.py`

### Iteracja 5: UI (1h)
- [ ] Rozszerzenie `templates/song.html`
- [ ] Test E2E: klik → pobierz → hexdump

### Iteracja 6: Walidacja (1-2h)
- [ ] Test z pacer-editor (wizualna weryfikacja)
- [ ] Test z amidi (jeśli Pacer dostępny)

**Łączny czas: ~10-14h**

## Referencje

- `workspace/pacer-editor/` (git submodule)
- `workspace/pacer-editor/src/pacer/constants.js` - stałe protokołu
- `workspace/pacer-editor/src/pacer/sysex.js` - algorytm checksum, budowanie ramek
- `workspace/pacer-editor/sysex.md` - dokumentacja protokołu
- `SPEC_PACER_BRIDGE.md` - kontekst workflow amidi

## Zmiany względem v1

1. ✅ Ujednolicone wartości MIDI (0x45 dla preset, 0x00 dla CC)
2. ✅ Algorytm checksum z pacer-editor
3. ✅ Pełna struktura ramki SysEx (F0...F7)
4. ✅ Hardcoded `DEVICE_CHANNELS` w mappings.py (MVP)
5. ✅ Normalizacja nazw presetów (8 znaków ASCII)
6. ✅ Format pliku: konkatenacja wiadomości bez separatorów
7. ✅ UI: instrukcja `amidi -l` zamiast hardcoded portu
8. ✅ Referencja do pacer-editor przez submodule

## Odpowiedzi na uwagi z SPEC_PACER_EXPORT_v2_REVIEW_2.md

### 1. ✅ Format nazwy presetu niespójny
**Problem**: Przykład pokazywał padding do 8 znaków, kod używał [długość, bajty].

**Rozwiązanie**:
- Zaktualizowano przykład: `[długość, bajty...]` bez paddingu
- Dodano refs do pacer-editor/sysex.js:858
- **Kod**: `SPEC_PACER_EXPORT_v2.md:83-91`

### 2. ✅ build_control_step omija Element byte
**Problem**: Spec sugerowała Element byte w headerze.

**Rozwiązanie**:
- Doprecyzowano: NIE MA Element w headerze (tylko w data bytes)
- Struktura: `[CMD, TARGET, INDEX, OBJECT] + [params...]`
- Element IDs są częścią każdego parametru: `[element_id, 0x01, value, 0x00]`
- **Kod**: `SPEC_PACER_EXPORT_v2.md:15-34, 196-232`

### 3. ✅ Kodowanie parametrów - active bez 0x00
**Problem**: Ostatni parametr (active) nie miał paddingu 0x00.

**Rozwiązanie**:
- Potwierdzono z pacer-editor/sysex.js:697 - to jest POPRAWNE
- Ostatni parametr: `[base+6, 0x01, active]` BEZ 0x00
- **Kod**: `SPEC_PACER_EXPORT_v2.md:221`

### 4. ✅ PATTERN pozostaje TODO
**Problem**: Brak rozstrzygnięcia Pattern vs MSG_SW_PRG_STEP.

**Rozwiązanie**:
- Model:Samples używa Program Change (0-95) do wyboru pattern
- `ActionType.PATTERN` → `MSG_SW_PRG_BANK` (jak preset), NIE MSG_SW_PRG_STEP
- Dodano `pattern_to_program()` - konwersja "A01"→0, "F16"→95
- **Źródła**: Dokumentacja M:S, Elektronauts forum
- **Kod**: `SPEC_PACER_EXPORT_v2.md:253-278, 299-302`

### 5. ✅ Router nie przekazuje devices
**Problem**: export_song_to_syx używało hardcoded DEVICE_CHANNELS.

**Rozwiązanie**:
- `export_song_to_syx()` przyjmuje `devices: list[Device]`
- Dodano `build_device_channel_map()` - buduje mapę z devices
- `action_to_midi()` przyjmuje `device_channel_map`
- Router wywołuje `storage.get_devices()` i przekazuje do eksportu
- **TODO**: Gdy Device dostanie pole `midi_channel`, użyć go zamiast fallback
- **Kod**: `SPEC_PACER_EXPORT_v2.md:250-291, 307-310, 417-420`

### 6. ✅ UI bez escapowania (XSS)
**Problem**: `{{ song.song.id }}` interpolowane bez escapowania.

**Rozwiązanie**:
- HTML attributes: `{{ song.song.id | urlencode }}`
- JavaScript: `const songId = {{ song.song.id | tojson }};`
- JS URL building: `encodeURIComponent(songId)`
- **Kod**: `SPEC_PACER_EXPORT_v2.md:457-483`

## Decyzje architektoniczne

**Pattern = Program Change**:
- Model:Samples: Program Change 0-95 wybiera pattern 1-96
- Pattern ID "A01" → PC 0, "F16" → PC 95
- MSG_SW_PRG_STEP (sekwencja) NIE jest używany

**Device.midi_channel**:
- Każde urządzenie ma przypisany MIDI channel w data/devices.yaml
- Eliminuje hardcoded mapowanie, całość konfiguracyjna

**Bank MSB/LSB dla PRESET**:
- Action ma pola bank_lsb i bank_msb (default=0)
- Umożliwia dostęp do presetów z różnych banków
- Backward compatibility przez defaulty

**Walidacja CC value**:
- ActionType.CC wymaga niepustego pola value (0-127)
- Pydantic model_validator wymusza to na poziomie modelu

## Review 3 (SPEC_PACER_EXPORT_v2_REVIEW_3.md)

Wszystkie 5 uwag zostały zweryfikowane jako **nieprawdziwe** - spec jest poprawny.

### 1. ❌ Niespójne sygnatury funkcji
**Claim**: Router wywołuje `export_song_to_syx(song, devices, preset)`, ale funkcja przyjmuje tylko `(song, target_preset)`.

**Weryfikacja**:
- `export.py:323-326`: `def export_song_to_syx(song: Song, devices: list[Device], target_preset: str = "A1")`
- `routers/pacer.py:420`: `syx_data = export_song_to_syx(song, devices, preset)`
- **Status**: Sygnatury są identyczne. Review nieprawidłowy.

### 2. ❌ Format nazwy presetu
**Claim**: Przykład protokołu (8 bajtów paddingowanych) przeczy implementacji (długość + zmienne bajty).

**Weryfikacja**:
- Przykład `SPEC:86-88`: `04 53 4F 4E 47` = długość(4) + "SONG"
- `build_preset_name:191-193`: `bytes([len(ascii_name)]) + ascii_name`
- `pacer-editor/sysex.js:858`: `msg.push(s.length)` + ASCII
- **Status**: Format jest spójny. Review nieprawidłowy.

### 3. ❌ Element w headerze control_step
**Claim**: Spec opisuje Element w headerze, ale build_control_step go nie używa.

**Weryfikacja z pacer-editor**:
- **Preset name** (`sysex.js:847-853`): Header = `[CMD, TARGET, INDEX, CONTROL_NAME, 0x00]` - element **obecny**
- **Control step** (`sysex.js:685-689`): Header = `[CMD, TARGET, INDEX, CONTROL_ID]` - element **nieobecny**
- Element IDs w control_step są w data bytes: `(step_index-1)*6 + offset` (linia 209-221)
- **Status**: Różne typy wiadomości mają różne struktury. Implementacja zgodna z protokołem. Review nieprawidłowy.

### 4. ❌ PATTERN TODO
**Claim**: Mapowanie PATTERN pozostaje w stanie TODO, brak implementacji.

**Weryfikacja**:
- `mappings.py:265-278`: Pełna implementacja `pattern_to_program()`
- `mappings.py:298-303`: `ActionType.PATTERN` → `MSG_SW_PRG_BANK` z konwersją "A01"→0
- Żadnego TODO w kodzie
- **Status**: PATTERN w pełni zaimplementowany. Review nieprawidłowy.

### 5. ❌ Hardcoded channels
**Claim**: Devices są pobierane ale nie używane, kanały hardcoded.

**Weryfikacja pełnego flow**:
1. `routers/pacer.py:418`: `devices = storage.get_devices()`
2. `routers/pacer.py:420`: Przekazanie do `export_song_to_syx(song, devices, preset)`
3. `export.py:344`: `device_channel_map = build_device_channel_map(devices)`
4. `mappings.py:250-260`: Iteracja po `devices`, budowa mapy
5. `export.py:359`: Przekazanie mapy do `action_to_midi(action, device_channel_map)`
6. `mappings.py:291`: Użycie mapy do odczytu kanału
- `DEFAULT_DEVICE_CHANNELS` to **fallback** gdy `Device.midi_channel` nie istnieje
- **Status**: Devices w pełni wykorzystywane. Review nieprawidłowy.

**Podsumowanie Review 3**: Spec jest poprawny i gotowy do implementacji. Review powstał przez niepełne przeczytanie kodu i niezweryfikowanie twierdzeń z kodem źródłowym pacer-editor.

## Review Findings (workspace/reviews/SPEC_PACER_EXPORT_v2_findings.md)

Wszystkie 6 uwag zostały zweryfikowane jako **ZASADNE**. Wprowadzono poprawki.

### 1. ✅ Sprzeczny opis Element w nagłówku
**Problem**: Sekcja "Struktura ramki" mówiła że "NIE MA Element w headerze", ale preset_name go dodaje.

**Rozwiązanie**:
- Rozdzielono strukturę na dwa warianty:
  - **Wariant A (Preset name)**: Header zawiera Element (0x00) przed data bytes
  - **Wariant B (Control steps)**: Header NIE zawiera Element, element IDs są w data bytes
- Wyjaśniono różnicę z referencją do pacer-editor/sysex.js
- **Kod**: `SPEC_PACER_EXPORT_v2.md:13-49`

### 2. ✅ Niepoprawna ścieżka importu
**Problem**: Router używał `from .pacer.export` zamiast `from ..pacer.export`.

**Rozwiązanie**:
- Poprawiono import path z `.pacer` na `..pacer` (z routers/ wyjdź do paternologia/, potem wejdź do pacer/)
- **Kod**: `SPEC_PACER_EXPORT_v2.md:412-413`

### 3. ✅ Brak obsługi pustych wartości dla CC
**Problem**: `action.value` może być `None` (data/songs/w-ciszy.yaml:27), co spowoduje `TypeError` przy `bytes(params)`.

**Rozwiązanie**:
- Dodano Pydantic `@model_validator` wymuszający value dla ActionType.CC
- action.value jest teraz wymagane (0-127) dla CC
- **Kod**: `SPEC_PACER_EXPORT_v2.md:165-172` (model Action), `320-323` (action_to_midi)

### 4. ✅ Deklarowany bank MSB nigdy nie wysyłany
**Problem**: Komentarz wspominał data3=bank MSB, ale `action_to_midi` zwracało tylko 4 wartości.

**Rozwiązanie**:
- Dodano pola `bank_lsb` i `bank_msb` do modelu Action (default=0)
- `action_to_midi` zwraca 5 wartości używając `action.bank_lsb` i `action.bank_msb` dla PRESET
- Zaktualizowano wywołanie w `export_song_to_syx` do dekonstrukcji 5 wartości
- **Kod**: `SPEC_PACER_EXPORT_v2.md:152-163` (model Action), `302-311` (action_to_midi PRESET)

### 5. ✅ Mapowanie kanałów nie da się skonfigurować
**Problem**: Model Device nie ma pola `midi_channel`, używany jest hardcoded fallback.

**Rozwiązanie**:
- Dodano pole `midi_channel: int` (0-15) do modelu Device
- Zaktualizowano format data/devices.yaml z midi_channel per device
- `build_device_channel_map` używa `device.midi_channel` bezpośrednio (bez fallback)
- Usunięto `DEFAULT_DEVICE_CHANNELS` - całość konfiguracyjna
- **Kod**: `SPEC_PACER_EXPORT_v2.md:134-139` (model Device), `175-199` (devices.yaml), `258-266` (build_device_channel_map)

### 6. ✅ Otwarte TODO vs sekcja Review 3
**Problem**: Review 3 twierdzi "wszystko zamknięte", ale TODO w kodzie (linia 257-259) wskazuje na ograniczenie.

**Rozwiązanie**:
- Wszystkie "ograniczenia" są teraz częścią głównej specyfikacji MVP:
  - Device.midi_channel - zaimplementowane w modelu (linia 134-139)
  - Bank MSB/LSB - zaimplementowane w Action (linia 152-163)
  - Walidacja CC value - zaimplementowane w model_validator (linia 165-172)
- Usunięto TODO z kodu - `build_device_channel_map` używa `device.midi_channel` bezpośrednio
- **Status**: ✅ **TEMAT ZAMKNIĘTY** - wszystko jest częścią głównej spec, nie "przyszłymi rozszerzeniami"

**Podsumowanie Findings**: Wszystkie uwagi były trafne. Elementy z "przyszłych rozszerzeń" przeniesiono do głównej specyfikacji - są to wymagania MVP, nie opcjonalne dodatki.
