# ABOUTME: Tests for MIDI port detection utilities.
# ABOUTME: Tests amidi output parsing and rtmidi port search.

import subprocess


from paternologia.midi.ports import (
    find_amidi_port,
    find_rtmidi_output_port,
    find_rtmidi_ports,
    pacer_input_subscribed,
)


# Realistic `aconnect -l` output under LC_ALL=C, PACER input subscribed by the bridge.
_ACONNECT_SUBSCRIBED = """\
client 14: 'Midi Through' [type=kernel]
    0 'Midi Through Port-0'
client 44: 'PACER' [type=kernel,card=7]
    0 'PACER MIDI1     '
	Connecting To: 129:0
    1 'PACER MIDI2     '
	Connecting To: 130:0
client 52: 'RC-600' [type=kernel,card=9]
    0 'RC-600 MIDI 1   '
client 129: 'RtMidiIn Client' [type=user,pid=3921885]
    0 'RtMidi input    '
	Connected From: 44:0
"""

# Same rig after PACER re-enumeration: PACER block has no subscription anymore,
# even though the stale RtMidiIn client still exists.
_ACONNECT_STALE = """\
client 14: 'Midi Through' [type=kernel]
    0 'Midi Through Port-0'
client 44: 'PACER' [type=kernel,card=7]
    0 'PACER MIDI1     '
    1 'PACER MIDI2     '
client 52: 'RC-600' [type=kernel,card=9]
    0 'RC-600 MIDI 1   '
client 129: 'RtMidiIn Client' [type=user,pid=3921885]
    0 'RtMidi input    '
"""


def _fake_run(stdout, returncode=0):
    def run(*a, **kw):
        return subprocess.CompletedProcess(a[0], returncode, stdout=stdout, stderr="")

    return run


class TestPacerInputSubscribed:
    """Tests for pacer_input_subscribed - honest ALSA subscription check."""

    def test_true_when_device_output_subscribed(self, monkeypatch):
        """PACER output port has a 'Connecting To:' line -> subscribed."""
        monkeypatch.setattr(subprocess, "run", _fake_run(_ACONNECT_SUBSCRIBED))
        assert pacer_input_subscribed("PACER") is True

    def test_false_when_subscription_dropped(self, monkeypatch):
        """PACER present but no 'Connecting To:' after re-enumeration -> not subscribed."""
        monkeypatch.setattr(subprocess, "run", _fake_run(_ACONNECT_STALE))
        assert pacer_input_subscribed("PACER") is False

    def test_false_when_device_absent(self, monkeypatch):
        """No PACER client block at all -> not subscribed."""
        no_pacer = (
            "client 14: 'Midi Through' [type=kernel]\n    0 'Midi Through Port-0'\n"
        )
        monkeypatch.setattr(subprocess, "run", _fake_run(no_pacer))
        assert pacer_input_subscribed("PACER") is False

    def test_subscription_of_other_client_does_not_leak(self, monkeypatch):
        """A 'Connecting To:' under a different client must not count for PACER."""
        other = (
            "client 44: 'PACER' [type=kernel,card=7]\n"
            "    0 'PACER MIDI1     '\n"
            "client 52: 'RC-600' [type=kernel,card=9]\n"
            "    0 'RC-600 MIDI 1   '\n"
            "\tConnecting To: 200:0\n"
        )
        monkeypatch.setattr(subprocess, "run", _fake_run(other))
        assert pacer_input_subscribed("PACER") is False

    def test_false_when_only_substring_named_client_subscribed(self, monkeypatch):
        """A different client whose NAME merely contains the device name must not count.

        Re-enumeration trap: a stale/monitor client 'PACER-monitor' carries a live
        subscription while the real 'PACER' block has none. Substring matching would
        report subscribed=True (masking a dead input); exact client-name match must
        return False.
        """
        collision = (
            "client 44: 'PACER' [type=kernel,card=7]\n"
            "    0 'PACER MIDI1     '\n"
            "client 60: 'PACER-monitor' [type=user,pid=999]\n"
            "    0 'monitor in      '\n"
            "\tConnecting To: 200:0\n"
        )
        monkeypatch.setattr(subprocess, "run", _fake_run(collision))
        assert pacer_input_subscribed("PACER") is False

    def test_true_on_timeout(self, monkeypatch):
        """aconnect timing out -> assume subscribed (degrade, do not churn)."""

        def raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired(cmd=["aconnect", "-l"], timeout=2)

        monkeypatch.setattr(subprocess, "run", raise_timeout)
        assert pacer_input_subscribed("PACER") is True

    def test_forces_c_locale(self, monkeypatch):
        """aconnect is invoked with LC_ALL=C so labels are stable English."""
        captured = {}

        def run(*a, **kw):
            captured["env"] = kw.get("env")
            return subprocess.CompletedProcess(
                a[0], 0, stdout=_ACONNECT_SUBSCRIBED, stderr=""
            )

        monkeypatch.setattr(subprocess, "run", run)
        pacer_input_subscribed("PACER")
        assert captured["env"]["LC_ALL"] == "C"

    def test_true_on_command_failure(self, monkeypatch):
        """aconnect failing -> assume subscribed (degrade, do not churn reconnects)."""
        monkeypatch.setattr(subprocess, "run", _fake_run("", returncode=1))
        assert pacer_input_subscribed("PACER") is True

    def test_true_when_aconnect_missing(self, monkeypatch):
        """aconnect binary absent -> assume subscribed."""

        def raise_fnf(*a, **kw):
            raise FileNotFoundError("aconnect not found")

        monkeypatch.setattr(subprocess, "run", raise_fnf)
        assert pacer_input_subscribed("PACER") is True


class TestFindAmidiPort:
    """Tests for find_amidi_port - parsing amidi -l output."""

    def test_finds_pacer_port(self, monkeypatch):
        """Should parse amidi -l output and find PACER port."""
        fake_output = (
            "Dir Device    Name\n"
            "IO  hw:4,0,0  PACER MIDI1\n"
            "IO  hw:5,0,0  USB MIDI Interface\n"
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0], 0, stdout=fake_output, stderr=""
            ),
        )
        assert find_amidi_port("PACER") == "hw:4,0,0"

    def test_returns_none_when_not_found(self, monkeypatch):
        """Should return None when device not in amidi output."""
        fake_output = "Dir Device    Name\nIO  hw:5,0,0  USB MIDI Interface\n"
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0], 0, stdout=fake_output, stderr=""
            ),
        )
        assert find_amidi_port("PACER") is None

    def test_case_insensitive_search(self, monkeypatch):
        """Should match device name case-insensitively."""
        fake_output = "Dir Device    Name\nIO  hw:4,0,0  Pacer midi1\n"
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0], 0, stdout=fake_output, stderr=""
            ),
        )
        assert find_amidi_port("pacer") == "hw:4,0,0"

    def test_returns_none_on_command_failure(self, monkeypatch):
        """Should return None if amidi command fails."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0], 1, stdout="", stderr="error"
            ),
        )
        assert find_amidi_port("PACER") is None

    def test_returns_none_on_file_not_found(self, monkeypatch):
        """Should return None if amidi binary not found."""

        def raise_fnf(*a, **kw):
            raise FileNotFoundError("amidi not found")

        monkeypatch.setattr(subprocess, "run", raise_fnf)
        assert find_amidi_port("PACER") is None


class TestFindRtmidiPorts:
    """Tests for find_rtmidi_ports - all matching input ports."""

    def test_finds_all_matching_ports(self, monkeypatch):
        """Returns every port index whose name contains the device name."""
        import rtmidi

        class FakeMidiIn:
            def delete(self):
                pass

            def get_ports(self):
                return [
                    "Midi Through:Midi Through Port-0 14:0",
                    "PACER:PACER MIDI1 48:0",
                    "PACER:PACER MIDI2 48:1",
                ]

        monkeypatch.setattr(rtmidi, "MidiIn", FakeMidiIn)
        assert find_rtmidi_ports("PACER") == [1, 2]

    def test_empty_when_none_match(self, monkeypatch):
        """Returns an empty list when no port matches."""
        import rtmidi

        class FakeMidiIn:
            def delete(self):
                pass

            def get_ports(self):
                return ["Midi Through:Midi Through Port-0 14:0"]

        monkeypatch.setattr(rtmidi, "MidiIn", FakeMidiIn)
        assert find_rtmidi_ports("PACER") == []


class TestFindRtmidiOutputPort:
    """Tests for find_rtmidi_output_port - first matching output port."""

    def test_finds_virmidi_output(self, monkeypatch):
        """Returns the first output port index matching the hint."""
        import rtmidi

        class FakeMidiOut:
            def delete(self):
                pass

            def get_ports(self):
                return [
                    "Midi Through:Midi Through Port-0 14:0",
                    "Virtual Raw MIDI 11-0:VirMIDI 11-0 60:0",
                ]

        monkeypatch.setattr(rtmidi, "MidiOut", FakeMidiOut)
        assert find_rtmidi_output_port("VirMIDI") == 1

    def test_none_when_no_match(self, monkeypatch):
        """Returns None when no output port matches the hint."""
        import rtmidi

        class FakeMidiOut:
            def delete(self):
                pass

            def get_ports(self):
                return ["Midi Through:Midi Through Port-0 14:0"]

        monkeypatch.setattr(rtmidi, "MidiOut", FakeMidiOut)
        assert find_rtmidi_output_port("VirMIDI") is None
