# ABOUTME: Tests for MIDI port detection utilities.
# ABOUTME: Tests amidi output parsing and rtmidi port search.

import subprocess


from paternologia.midi.ports import (
    find_amidi_port,
    find_rtmidi_output_port,
    find_rtmidi_port,
    find_rtmidi_ports,
)


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


class TestFindRtmidiPort:
    """Tests for find_rtmidi_port - searching rtmidi port list."""

    def test_finds_port_by_name(self, monkeypatch):
        """Should find port index matching device name."""
        fake_ports = [
            "Midi Through:Midi Through Port-0 14:0",
            "PACER:PACER MIDI 1 20:0",
        ]

        import rtmidi

        class FakeMidiIn:
            def delete(self):
                pass

            def get_ports(self):
                return fake_ports

        monkeypatch.setattr(rtmidi, "MidiIn", FakeMidiIn)
        assert find_rtmidi_port("PACER") == 1

    def test_returns_none_when_not_found(self, monkeypatch):
        """Should return None when no port matches."""
        import rtmidi

        class FakeMidiIn:
            def delete(self):
                pass

            def get_ports(self):
                return ["Midi Through:Midi Through Port-0 14:0"]

        monkeypatch.setattr(rtmidi, "MidiIn", FakeMidiIn)
        assert find_rtmidi_port("PACER") is None

    def test_case_insensitive(self, monkeypatch):
        """Should match case-insensitively."""
        import rtmidi

        class FakeMidiIn:
            def delete(self):
                pass

            def get_ports(self):
                return ["pacer:pacer midi 1 20:0"]

        monkeypatch.setattr(rtmidi, "MidiIn", FakeMidiIn)
        assert find_rtmidi_port("PACER") == 0


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
