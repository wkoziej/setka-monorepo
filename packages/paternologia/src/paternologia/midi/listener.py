# ABOUTME: MIDI listener using python-rtmidi for live song detection.
# ABOUTME: Listens for Program Change messages and publishes events via EventBus.

import logging
from collections.abc import Callable

import rtmidi

from paternologia.midi.bridge import MidiBridge
from paternologia.midi.events import EventBus, MidiEvent
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.ports import find_rtmidi_ports, pacer_input_subscribed

logger = logging.getLogger(__name__)

# System Real-Time messages (clock, start/stop, active sensing, reset) start here.
_SYSTEM_REALTIME_MIN = 0xF8

# Consecutive "subscription not seen" polls required before tearing down a live
# input. A single aconnect read can be a transient/partial snapshot mid
# re-enumeration; acting on it would drop footswitch presses on a working input.
_RESUBSCRIBE_STRIKES = 2


class MidiListener:
    """Listens for MIDI Program Change and publishes matching song events."""

    def __init__(
        self,
        song_index: SongMidiIndex,
        event_bus: EventBus,
        bridge: MidiBridge | None = None,
    ):
        self._index = song_index
        self._bus = event_bus
        self._bridge = bridge
        self._midi_ins: list[rtmidi.MidiIn] = []
        self._device_name: str | None = None
        self._on_record_trigger: Callable[[str], None] | None = None
        self._trigger_channel: int | None = None
        self._start_note: int | None = None
        self._stop_note: int | None = None
        self._trigger_port: str | None = None
        self._unsubscribed_strikes = 0

    def configure_record_trigger(
        self,
        channel: int,
        start_note: int,
        stop_note: int,
        callback: Callable[[str], None],
        port: str | None = None,
    ) -> None:
        """Wire PACER record triggers: Note On(start/stop) on `channel` -> callback.

        callback is invoked from the rtmidi C thread with "start" / "stop"; the
        caller is responsible for marshalling off this thread (network I/O).

        When ``port`` is set, only Note On messages arriving on a port whose name
        contains that substring (e.g. "MIDI2") fire the trigger — so a stray
        note 94/93 on a different PACER port can't start/stop recording. ``None``
        accepts the trigger on any open port.
        """
        self._trigger_channel = channel
        self._start_note = start_note
        self._stop_note = stop_note
        self._on_record_trigger = callback
        self._trigger_port = port

    @property
    def song_index(self) -> SongMidiIndex:
        return self._index

    @song_index.setter
    def song_index(self, index: SongMidiIndex) -> None:
        self._index = index

    @property
    def is_active(self) -> bool:
        """True when at least one hardware input port is currently open."""
        return len(self._midi_ins) > 0

    @property
    def input_subscribed(self) -> bool:
        """True only if a port is open AND ALSA still subscribes it to the device.

        Honest signal for /health: ``is_active`` alone stays True after the PACER
        re-enumerates, even though the subscription is gone (see
        ``pacer_input_subscribed``).

        Fail-open: when the ALSA check itself can't run (aconnect missing/erroring/
        timing out) this reports True, so /health over-reports rather than churning
        reconnects — i.e. a green ``pacer_input_open`` is not a hard guarantee on a
        host where aconnect is broken.
        """
        if not self.is_active or self._device_name is None:
            return False
        return pacer_input_subscribed(self._device_name)

    def start(self, device_name: str) -> bool:
        """Open ALL ports matching device_name (e.g. PACER MIDI1 + MIDI2).

        A footswitch trigger may arrive on a secondary port (a note on MIDI2),
        so Model A must read every matching port. Returns True if any opened.
        """
        self._device_name = device_name
        port_indices = find_rtmidi_ports(device_name)
        if not port_indices:
            logger.warning(
                "MIDI port for '%s' not found, listener inactive", device_name
            )
            return False

        for port_idx in port_indices:
            try:
                midi_in = rtmidi.MidiIn()
                midi_in.open_port(port_idx)
                try:
                    port_name = midi_in.get_port_name(port_idx)
                except Exception:
                    port_name = device_name
                # Pass the port name as callback data so record-trigger scoping
                # can tell which physical PACER port a note arrived on.
                midi_in.set_callback(self._callback, data=port_name)
                self._midi_ins.append(midi_in)
                logger.info(
                    "MIDI listener started on port %d (%s)", port_idx, port_name
                )
            except Exception as e:
                logger.warning("Failed to open MIDI port %d: %s", port_idx, e)

        return self.is_active

    def start_virtual(self, port_name: str) -> None:
        """Start listening on a virtual MIDI port (for testing)."""
        midi_in = rtmidi.MidiIn()
        midi_in.open_virtual_port(port_name)
        midi_in.set_callback(self._callback, data=port_name)
        self._midi_ins.append(midi_in)
        logger.info("MIDI listener started on virtual port '%s'", port_name)

    def stop(self) -> None:
        """Stop listening and close all MIDI ports."""
        if not self._midi_ins:
            return
        for midi_in in self._midi_ins:
            midi_in.close_port()
            # delete() frees the underlying ALSA seq client immediately; plain
            # `del` leaks it (reference cycle) and exhausts /dev/snd/seq.
            midi_in.delete()
        self._midi_ins.clear()
        logger.info("MIDI listener stopped")

    def poll_reconnect(self) -> None:
        """Reopen the PACER inputs after replug/re-enumeration, or release them.

        ALSA port indices shift on replug, so we re-match by name. The bridge
        output port is unaffected and stays open the whole time.

        Re-enumeration (replug, suspend/resume, card-number change) is the subtle
        case: rtmidi keeps the MidiIn handle "open" (``is_active`` stays True)
        while ALSA silently drops the subscription. Handle count alone can't see
        that, so when ports are present and handles are open we additionally
        verify the real subscription and reopen if it was lost.
        """
        if self._device_name is None:
            return
        ports_present = bool(find_rtmidi_ports(self._device_name))
        if not ports_present:
            self._unsubscribed_strikes = 0
            if self.is_active:
                logger.warning(
                    "PACER '%s' disappeared; releasing inputs", self._device_name
                )
                self.stop()
            return
        if not self.is_active:
            self._unsubscribed_strikes = 0
            logger.info("PACER '%s' reappeared; reopening inputs", self._device_name)
            self.start(self._device_name)
            return
        if pacer_input_subscribed(self._device_name):
            self._unsubscribed_strikes = 0
            return
        # Subscription not seen. Defer the teardown until it persists across
        # consecutive polls (hysteresis) — a lone negative read is likely a
        # transient/partial aconnect snapshot, and stop+start on a working input
        # drops footswitch presses mid-set.
        self._unsubscribed_strikes += 1
        if self._unsubscribed_strikes < _RESUBSCRIBE_STRIKES:
            logger.debug(
                "PACER '%s' subscription not seen (%d/%d); deferring reopen",
                self._device_name,
                self._unsubscribed_strikes,
                _RESUBSCRIBE_STRIKES,
            )
            return
        logger.warning(
            "PACER '%s' input subscription lost (re-enumeration); reopening",
            self._device_name,
        )
        self._unsubscribed_strikes = 0
        self.stop()
        self.start(self._device_name)

    def _trigger_port_matches(self, data) -> bool:
        """True if the record trigger is allowed on the port that delivered it."""
        if self._trigger_port is None:
            return True
        return data is not None and self._trigger_port.upper() in str(data).upper()

    def _callback(self, event, data=None) -> None:
        """rtmidi callback - runs on a separate C thread.

        Wraps the handler so no exception escapes into the rtmidi C thread (which
        could silently kill MIDI input). ``data`` is the originating port name.
        """
        try:
            self._handle(event, data)
        except Exception as e:
            logger.warning("MIDI callback error: %s", e)

    def _handle(self, event, data) -> None:
        message, _deltatime = event
        if not message:
            return

        status = message[0]

        # Fan-out (Model A): relay everything except System Real-Time to the
        # bridge so Bitwig sees the full PACER stream (CC/PC/Note triggers). A
        # bridge failure must not skip record-trigger detection below.
        if self._bridge is not None and status < _SYSTEM_REALTIME_MIN:
            try:
                self._bridge.send(message)
            except Exception as e:
                logger.warning("bridge fan-out failed: %s", e)

        # Record triggers: Note On (velocity > 0) on the configured channel/notes,
        # optionally scoped to a specific port (e.g. PACER MIDI2).
        if (
            self._on_record_trigger is not None
            and (status & 0xF0) == 0x90
            and len(message) >= 3
            and message[2] > 0
            and (status & 0x0F) == self._trigger_channel
            and self._trigger_port_matches(data)
        ):
            if message[1] == self._start_note:
                logger.info("PACER record trigger: START")
                self._on_record_trigger("start")
            elif message[1] == self._stop_note:
                logger.info("PACER record trigger: STOP")
                self._on_record_trigger("stop")

        # Program Change: 0xCn where n is channel (0-15)
        if len(message) < 2 or (status & 0xF0) != 0xC0:
            return

        channel = status & 0x0F
        program = message[1]

        logger.debug("Program Change: ch=%d prog=%d", channel, program)

        song_id = self._index.lookup(channel, program)
        if song_id is None:
            logger.debug("No song mapped to ch=%d prog=%d", channel, program)
            return

        logger.info("MIDI → song '%s' (ch=%d, prog=%d)", song_id, channel, program)
        self._bus.publish_threadsafe(
            MidiEvent(
                song_id=song_id,
                channel=channel,
                program=program,
            )
        )
