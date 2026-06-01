# ABOUTME: FastAPI application entry point for Paternologia.
# ABOUTME: Configures app with Jinja2 templates, static files, and API routers.

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from paternologia.dependencies import get_storage
from paternologia.midi.events import EventBus
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.listener import MidiListener
from paternologia.routers import devices_router, live_router, pacer_router, songs_router

# Configure logging to show ERROR and above
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"


def _build_midi_index(storage) -> SongMidiIndex:
    """Build reverse MIDI index from current songs and devices."""
    songs = storage.get_songs()
    devices = storage.get_devices()
    return SongMidiIndex.build(songs, devices)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    storage = get_storage()
    storage._ensure_dirs()

    # MIDI subsystem
    event_bus = EventBus()
    event_bus.set_loop(asyncio.get_running_loop())
    app.state.event_bus = event_bus

    midi_index = _build_midi_index(storage)
    app.state.midi_index = midi_index

    # Start MIDI listener (graceful degradation if no device)
    pacer_config = storage.get_pacer_config()
    device_name = pacer_config.device_name if pacer_config else "PACER"

    try:
        listener = MidiListener(song_index=midi_index, event_bus=event_bus)
        if listener.start(device_name):
            app.state.midi_listener = listener
            logger.info("MIDI listener active for '%s'", device_name)
        else:
            app.state.midi_listener = None
            logger.warning("MIDI listener inactive — no '%s' device found", device_name)
    except Exception as e:
        app.state.midi_listener = None
        logger.warning("MIDI listener failed to start: %s", e)

    yield

    # Shutdown
    if app.state.midi_listener is not None:
        app.state.midi_listener.stop()


app = FastAPI(
    title="Paternologia",
    description="MIDI configuration manager for songs",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(songs_router)
app.include_router(devices_router)
app.include_router(pacer_router)
app.include_router(live_router)
