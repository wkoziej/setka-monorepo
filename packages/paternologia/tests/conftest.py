# ABOUTME: Shared pytest configuration for the paternologia test suite.
# ABOUTME: Disables the lifespan MIDI subsystem so HTTP tests need no ALSA hardware.

import os

# Tests that exercise MIDI (test_midi_bridge, test_midi_listener) construct the
# bridge/listener directly and bypass the app lifespan. Every other test that
# spins up the FastAPI app via TestClient must NOT grab real ALSA ports, both for
# speed and to avoid exhausting /dev/snd/seq across hundreds of lifespans.
os.environ.setdefault("PATERNOLOGIA_DISABLE_MIDI", "1")
