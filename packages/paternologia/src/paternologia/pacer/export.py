# ABOUTME: Main export function for generating Pacer .syx files from songs.
# ABOUTME: Concatenates SysEx messages for preset name and control steps.

from ..models import Song, Device
from .sysex import PacerSysExBuilder
from .mappings import action_to_midi, build_device_channel_map
from . import constants as c


def export_song_to_syx(
    song: Song, devices: list[Device], target_preset: str = "A1"
) -> bytes:
    """Eksportuj piosenkę do pliku .syx.

    Args:
        song: Piosenka z Paternologii
        devices: Lista urządzeń (do mapowania device_id → MIDI channel)
        target_preset: Preset docelowy (CURRENT, A1-D6)

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

        # 2a. Control Mode (musi być przed steps!) - mode=0 = "all steps in one shot"
        messages.append(builder.build_control_mode(control_id, mode=0))

        # 2b. Zawsze konfiguruj wszystkie 6 kroków (czyszczenie niewykorzystanych)
        for step_idx in range(1, 7):
            if button and step_idx <= len(button.actions):
                # Akcja istnieje - konfiguruj normalnie
                action = button.actions[step_idx - 1]
                msg_type, channel, data1, data2, data3 = action_to_midi(
                    action, device_channel_map
                )
                messages.append(
                    builder.build_control_step(
                        control_id=control_id,
                        step_index=step_idx,
                        msg_type=msg_type,
                        channel=channel,
                        data1=data1,
                        data2=data2,
                        data3=data3,
                        active=True,
                    )
                )
            else:
                # Brak akcji - wyczyść krok (MSG_CTRL_OFF, active=False)
                messages.append(
                    builder.build_control_step(
                        control_id=control_id,
                        step_index=step_idx,
                        msg_type=c.MSG_CTRL_OFF,
                        channel=0,
                        data1=0,
                        data2=0,
                        data3=0,
                        active=False,
                    )
                )

        # 2c. Konfiguracja LED dla WSZYSTKICH 6 stepów (pacer wymaga LED dla każdego stepu)
        has_actions = button and len(button.actions) > 0
        for step_idx in range(1, 7):
            if has_actions:
                messages.append(
                    builder.build_control_led(
                        control_id=control_id,
                        step_index=step_idx,
                        active_color=c.LED_BLUE,
                        inactive_color=c.LED_AMBER,
                    )
                )
            else:
                # Przycisk bez akcji - LED wyłączony
                messages.append(
                    builder.build_control_led(
                        control_id=control_id,
                        step_index=step_idx,
                        active_color=c.LED_OFF,
                        inactive_color=c.LED_OFF,
                    )
                )

    return b"".join(messages)
