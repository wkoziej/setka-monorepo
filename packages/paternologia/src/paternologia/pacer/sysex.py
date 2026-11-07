# ABOUTME: SysEx message builder for Nektar Pacer.
# ABOUTME: Generates properly formatted SysEx frames with checksum.

from . import constants as c

# Checksum obejmuje bajty od CMD do końca danych — bez nagłówka
# F0 + Manufacturer ID + Device ID (tak liczy Pacer w dumpie i pacer-editor).
_CHECKSUM_START = len(c.MANUFACTURER_ID) + 1


def checksum(data: bytes) -> int:
    """Checksum Pacera: (128 - suma % 128) % 128 dla bajtów od CMD do końca danych."""
    return (128 - (sum(data) % 128)) % 128


class PacerSysExBuilder:
    """Buduje pojedyncze wiadomości SysEx."""

    def __init__(self, preset_index: int):
        self.preset_index = preset_index

    def _build_preset_name_frame(self, data: bytes) -> bytes:
        """Ramka SysEx dla preset name (z Element w headerze)."""
        header = bytes(
            [
                c.DEVICE_ID,
                c.CMD_SET,
                c.TARGET_PRESET,
                self.preset_index,
                c.CONTROL_NAME,
                0x00,  # Element = 0 dla preset name
            ]
        )
        payload = c.MANUFACTURER_ID + header + data
        cs = checksum(payload[_CHECKSUM_START:])
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])

    def build_preset_name(self, name: str) -> bytes:
        """Ustaw nazwę presetu (dynamiczna długość, max 8 ASCII)."""
        ascii_name = name.encode("ascii", errors="replace")[:8]
        # Format: [długość] [bajty ASCII...]
        data = bytes([len(ascii_name)]) + ascii_name
        return self._build_preset_name_frame(data)

    def build_control_step(
        self,
        control_id: int,
        step_index: int,
        msg_type: int,
        channel: int,
        data1: int,
        data2: int = 0,
        data3: int = 0,
        active: bool = True,
    ) -> bytes:
        """Konfiguruj krok kontrolki.

        Struktura: dla każdego parametru: [element_id, 0x01, wartość, 0x00]
        gdzie element_id = (step_index-1)*6 + offset
        Ostatni parametr (active) NIE ma paddingu 0x00.
        """
        base = (step_index - 1) * 6
        return self._build_elements_frame(
            control_id,
            [
                (base + 1, channel),
                (base + 2, msg_type),
                (base + 3, data1),
                (base + 4, data2),
                (base + 5, data3),
                (base + 6, int(active)),
            ],
        )

    def build_control_mode(self, control_id: int, mode: int = 0) -> bytes:
        """Ustaw tryb kontrolki.

        Args:
            control_id: ID kontrolki (0x0D-0x12 dla SW1-SW6)
            mode: Tryb (0=all steps in one shot, 1=toggle, etc.)
        """
        return self._build_elements_frame(control_id, [(c.CONTROL_MODE_ELEMENT, mode)])

    def build_control_led(
        self,
        control_id: int,
        step_index: int,
        active_color: int = c.LED_AMBER,
        inactive_color: int = c.LED_OFF,
        led_midi_ctrl: int = 0,
        led_num: int = 0,
    ) -> bytes:
        """Konfiguruj LED dla kontrolki (konkretny step).

        Args:
            control_id: ID kontrolki (0x0D-0x12 dla SW1-SW6)
            step_index: Numer kroku (1-6)
            active_color: Kolor gdy aktywny (domyślnie amber)
            inactive_color: Kolor gdy nieaktywny (domyślnie off)
            led_midi_ctrl: CC do zdalnej kontroli (0=wyłączone)
            led_num: Która LED (0=default, 1=bottom, 2=middle, 3=top)
        """
        # LED elements: step1=0x40-0x43, step2=0x44-0x47, etc.
        base = (step_index - 1) * 4 + 0x40
        return self._build_elements_frame(
            control_id,
            [
                (base + 0, led_midi_ctrl),
                (base + 1, active_color),
                (base + 2, inactive_color),
                (base + 3, led_num),
            ],
        )

    def build_midi_config_entry(
        self,
        entry_index: int,
        msg_type: int,
        channel: int,
        data1: int,
        data2: int = 0,
        data3: int = 0,
    ) -> bytes:
        """Wpis M CFG: wiadomość wysyłana przez Pacer przy załadowaniu presetu.

        Każdy wpis to osobna ramka obiektu CONTROL_MIDI (0x7E) z 5 elementami
        (channel, typ, data1-3) pod numerami (entry_index-1)*6 + 1..5.
        Brak elementu active — tak jak w dumpie zwracanym przez Pacer.

        Args:
            entry_index: Numer wpisu (1-16)
            msg_type: Typ wiadomości (MSG_LOAD_CC, MSG_SW_PRG_BANK, MSG_SW_NOTE,
                MSG_CTRL_OFF)
            channel: Kanał MIDI (0 = Global, 1-16)
        """
        if not 1 <= entry_index <= c.MIDI_CONFIG_ENTRIES:
            raise ValueError(
                f"entry_index musi być 1-{c.MIDI_CONFIG_ENTRIES}, jest {entry_index}"
            )
        if not 0 <= channel <= 16:
            raise ValueError(f"channel musi być 0-16, jest {channel}")
        for name, value in (
            ("msg_type", msg_type),
            ("data1", data1),
            ("data2", data2),
            ("data3", data3),
        ):
            if not 0 <= value <= 127:
                raise ValueError(f"{name} musi być 0-127, jest {value}")

        base = (entry_index - 1) * 6
        return self._build_elements_frame(
            c.CONTROL_MIDI,
            [
                (base + 1, channel),
                (base + 2, msg_type),
                (base + 3, data1),
                (base + 4, data2),
                (base + 5, data3),
            ],
        )

    def build_empty_midi_config_entry(self, entry_index: int) -> bytes:
        """Wyczyszczony wpis M CFG (typ OFF) — Pacer nic nie wysyła."""
        return self.build_midi_config_entry(
            entry_index, msg_type=c.MSG_CTRL_OFF, channel=0, data1=0
        )

    def _build_elements_frame(
        self, object_id: int, elements: list[tuple[int, int]]
    ) -> bytes:
        """Ramka SET dla obiektu presetu z listą elementów.

        Każdy element: [element_id, 0x01, wartość, 0x00]; ostatni bez
        paddingu 0x00.
        """
        params: list[int] = []
        for element_id, value in elements:
            params.extend([element_id, 0x01, value, 0x00])
        params.pop()  # Ostatni element bez paddingu

        header = bytes(
            [c.DEVICE_ID, c.CMD_SET, c.TARGET_PRESET, self.preset_index, object_id]
        )
        payload = c.MANUFACTURER_ID + header + bytes(params)
        cs = checksum(payload[_CHECKSUM_START:])
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])
