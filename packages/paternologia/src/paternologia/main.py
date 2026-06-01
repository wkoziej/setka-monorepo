# ABOUTME: FastAPI application entry point for Paternologia.
# ABOUTME: Configures app with Jinja2 templates, static files, and API routers.

import asyncio
import logging
import os
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from paternologia.dependencies import get_storage
from paternologia.midi.bridge import MidiBridge
from paternologia.midi.events import EventBus
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.listener import MidiListener
from paternologia.routers import (
    devices_router,
    health_router,
    live_router,
    pacer_router,
    songs_router,
)

# Configure logging to show ERROR and above
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"

# Poll interval for PACER replug detection and the systemd watchdog ping.
_WATCHER_INTERVAL_SEC = 2.0


def _build_midi_index(storage) -> SongMidiIndex:
    """Build reverse MIDI index from current songs and devices."""
    songs = storage.get_songs()
    devices = storage.get_devices()
    return SongMidiIndex.build(songs, devices)


def _sd_notify(message: str) -> None:
    """Send a systemd notification; no-op outside a systemd Type=notify unit."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    try:
        if addr.startswith("@"):
            addr = "\0" + addr[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(addr)
            sock.sendall(message.encode())
    except OSError as e:
        logger.debug("sd_notify failed: %s", e)


async def _replug_heartbeat_watcher(app: FastAPI) -> None:
    """Reopen PACER after replug and ping the systemd watchdog periodically."""
    while True:
        await asyncio.sleep(_WATCHER_INTERVAL_SEC)
        try:
            listener = app.state.midi_listener
            if listener is not None:
                listener.poll_reconnect()
            app.state.last_heartbeat_ts = time.time()
            _sd_notify("WATCHDOG=1")
        except Exception as e:  # never let the supervisor loop die
            logger.warning("replug/heartbeat watcher error: %s", e)


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

    # Bridge (Model A fan-out): create the virtual output port first so Bitwig
    # can subscribe even before/without a physical PACER being present.
    app.state.obs_connected = False  # set by the OBS client (plan 001 Unit 5)
    app.state.last_heartbeat_ts = None
    app.state.midi_bridge = None
    app.state.midi_listener = None
    watcher: asyncio.Task | None = None

    if os.environ.get("PATERNOLOGIA_DISABLE_MIDI"):
        logger.info("MIDI subsystem disabled (PATERNOLOGIA_DISABLE_MIDI set)")
    else:
        # Bridge (Model A fan-out): create the virtual output port first so Bitwig
        # can subscribe even before/without a physical PACER being present.
        bridge = MidiBridge()
        bridge.open()
        app.state.midi_bridge = bridge

        # Start MIDI listener (graceful degradation if no device). Always keep the
        # listener object so the replug watcher can reopen it when PACER returns.
        pacer_config = storage.get_pacer_config()
        device_name = pacer_config.device_name if pacer_config else "PACER"

        listener = MidiListener(
            song_index=midi_index, event_bus=event_bus, bridge=bridge
        )
        app.state.midi_listener = listener
        try:
            if listener.start(device_name):
                logger.info("MIDI listener active for '%s'", device_name)
            else:
                logger.warning(
                    "MIDI listener inactive — no '%s' device; will retry on replug",
                    device_name,
                )
        except Exception as e:
            logger.warning("MIDI listener failed to start: %s", e)

        watcher = asyncio.create_task(_replug_heartbeat_watcher(app))
        _sd_notify("READY=1")

    yield

    # Shutdown
    if watcher is not None:
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
    if app.state.midi_listener is not None:
        app.state.midi_listener.stop()
    if app.state.midi_bridge is not None:
        app.state.midi_bridge.close()


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
app.include_router(health_router)
