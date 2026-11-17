# ABOUTME: Main export function for generating Pacer .syx files from songs.
# ABOUTME: Concatenates SysEx messages for preset name, SW/FS control steps and M CFG.

from ..models import Action, Device, PacerConfig, Song
from . import constants as c
from .mappings import (
    action_to_midi,
    action_to_midi_config,
    build_device_channel_map,
    build_preset_cc_map,
)
from .sysex import PacerSysExBuilder


def export_song_to_syx(
    song: Song,
    devices: list[Device],
    target_preset: str = "A1",
    pacer_config: PacerConfig | None = None,
) -> bytes:
    """Eksportuj piosenkę do pliku .syx.

    Args:
        song: Piosenka z Paternologii
        devices: Lista urządzeń (do mapowania device_id → MIDI channel)
        target_preset: Preset docelowy (CURRENT, A1-D6)
        pacer_config: Konfiguracja Pacera (nuty triggera OBS do walidacji
            on_load); None = wartości domyślne, jak w main.py

    Returns:
        bytes: Zawartość pliku .syx (konkatenacja wiadomości)
    """
    preset_index = c.PRESET_INDICES[target_preset.upper()]
    builder = PacerSysExBuilder(preset_index)
    messages = []

    # Buduj mapę device_id → MIDI channel z devices
    device_channel_map = build_device_channel_map(devices)
    cc_release_same_devices = {d.id for d in devices if d.cc_release_same}
    preset_cc_devices = build_preset_cc_map(devices)

    # 1. Nazwa presetu
    messages.append(builder.build_preset_name(song.song.name))

    # 2. Konfiguracja przycisków SW1-SW6
    for btn_idx in range(6):  # Zawsze przetwarzaj wszystkie 6 przycisków
        control_id = c.STOMPSWITCHES[btn_idx]
        button = song.pacer[btn_idx] if btn_idx < len(song.pacer) else None

        messages.extend(
            _build_control_steps(
                builder,
                control_id,
                button.actions if button else [],
                device_channel_map,
                cc_release_same_devices,
                preset_cc_devices,
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

    # 3. Zewnętrzne footswitche FS1-FS4 (nieużywane wyczyszczone, bez LED)
    footswitches = {f.fs: f for f in song.footswitches}
    for fs_num, control_id in c.FOOTSWITCHES.items():
        footswitch = footswitches.get(fs_num)
        messages.extend(
            _build_control_steps(
                builder,
                control_id,
                footswitch.actions if footswitch else [],
                device_channel_map,
                cc_release_same_devices,
                preset_cc_devices,
            )
        )

    # 4. M CFG: wiadomości przy załadowaniu presetu. Zawsze wszystkie 16 wpisów,
    # nieużywane wyczyszczone — stan presetu w pełni określa YAML.
    config = pacer_config or PacerConfig()
    for entry_idx in range(1, c.MIDI_CONFIG_ENTRIES + 1):
        if entry_idx <= len(song.on_load):
            msg_type, channel, data1, data2, data3 = action_to_midi_config(
                song.on_load[entry_idx - 1],
                device_channel_map,
                config,
                preset_cc_devices,
            )
            messages.append(
                builder.build_midi_config_entry(
                    entry_idx, msg_type, channel, data1, data2, data3
                )
            )
        else:
            messages.append(builder.build_empty_midi_config_entry(entry_idx))

    return b"".join(messages)


def _build_control_steps(
    builder: PacerSysExBuilder,
    control_id: int,
    actions: list[Action],
    device_channel_map: dict[str, int],
    cc_release_same_devices: set[str],
    preset_cc_devices: dict[str, int],
) -> list[bytes]:
    """Ramki trybu i wszystkich 6 kroków kontrolki (SW lub FS).

    Kroki bez akcji są czyszczone (MSG_CTRL_OFF, active=False), żeby stan
    kontrolki w presecie w pełni określał YAML.
    """
    # Control Mode (musi być przed steps!) - mode=0 = "all steps in one shot"
    messages = [builder.build_control_mode(control_id, mode=0)]

    for step_idx in range(1, 7):
        if step_idx <= len(actions):
            # Akcja istnieje - konfiguruj normalnie
            msg_type, channel, data1, data2, data3 = action_to_midi(
                actions[step_idx - 1],
                device_channel_map,
                cc_release_same_devices,
                preset_cc_devices,
            )
            active = True
        else:
            # Brak akcji - wyczyść krok
            msg_type, channel, data1, data2, data3 = c.MSG_CTRL_OFF, 0, 0, 0, 0
            active = False
        messages.append(
            builder.build_control_step(
                control_id=control_id,
                step_index=step_idx,
                msg_type=msg_type,
                channel=channel,
                data1=data1,
                data2=data2,
                data3=data3,
                active=active,
            )
        )
    return messages
