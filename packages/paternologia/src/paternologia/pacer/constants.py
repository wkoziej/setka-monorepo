# ABOUTME: Protocol constants for Nektar Pacer SysEx communication.
# ABOUTME: Based on pacer-editor/src/pacer/constants.js and sysex.js.

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
MSG_CTRL_OFF = 0x61  # Kontrolka wyłączona
MSG_SW_PRG_BANK = (
    0x45  # Program Change + Bank: data1=program, data2=bank LSB, data3=bank MSB
)
MSG_SW_PRG_STEP = (
    0x46  # Program Step: data1=unused, data2=start, data3=end (start=end dla immediate)
)
MSG_SW_MIDI_CC = (
    0x40  # CC Trigger dla stompswitch: data1=controller, data2=down, data3=up
)
MSG_SW_MIDI_CC_TGGLE = (
    0x47  # CC Toggle dla stompswitch: data1=controller, data2=value1, data3=value2
)
MSG_SW_MIDI_CC_STEP = (
    0x48  # CC Step dla stompswitch: data1=controller, data2=start, data3=end
)
MSG_SW_NOTE = 0x43  # Note: data1=note, data2=velocity, data3=unused
# MSG_AD_MIDI_CC = 0x00 - NIE UŻYWAĆ dla stompswitch! To jest dla Expression Pedals

# LED colors (from pacer-editor dump_format.md)
# NOTE: 0x7F = OFF (not 0x00! 0x00 is Pink)
LED_OFF = 0x7F
LED_PINK = 0x01
LED_RED = 0x03
LED_ORANGE = 0x05
LED_AMBER = 0x07
LED_YELLOW = 0x09
LED_LIME = 0x0B
LED_GREEN = 0x0D
LED_TEAL = 0x0F
LED_BLUE = 0x11
LED_LAVENDER = 0x13
LED_PURPLE = 0x15
LED_WHITE = 0x17

# LED element offsets within a step (base + offset)
# Step 1: 0x40-0x43, Step 2: 0x44-0x47, etc.
LED_MIDI_CTRL_OFFSET = 0x40
LED_ACTIVE_COLOR_OFFSET = 0x41
LED_INACTIVE_COLOR_OFFSET = 0x42
LED_NUM_OFFSET = 0x43

# Preset indices according to Pacer protocol (from pacer-editor dumps/README.md)
# idx=0x00 = Current (writes to RAM, visible immediately)
# idx=0x01-0x18 = User presets A1-D6 (6 presets per bank)
# Formula: idx = (bank * 6) + col, where bank=0-3 (A-D), col=1-6
PRESET_INDEX_CURRENT = 0x00

PRESET_INDICES = {
    "CURRENT": PRESET_INDEX_CURRENT,
    **{
        f"{row}{col}": (ord(row) - ord("A")) * 6 + col
        for row in "ABCD"
        for col in range(1, 7)
    },
}
