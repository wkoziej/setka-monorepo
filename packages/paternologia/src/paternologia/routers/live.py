# ABOUTME: Live view router with SSE for real-time song display via MIDI.
# ABOUTME: Provides /live page, /live/events SSE stream, and /live/song/{id} partial.

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from paternologia.dependencies import get_storage, get_templates
from paternologia.midi.events import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live"])


def _get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


@router.get("/live", response_class=HTMLResponse)
async def live_page(request: Request):
    """Main live view page with SSE connection."""
    templates = get_templates()
    midi_connected = request.app.state.midi_listener is not None
    return templates.TemplateResponse(
        request=request,
        name="live.html",
        context={"midi_connected": midi_connected},
    )


@router.get("/live/events")
async def live_events(request: Request):
    """SSE endpoint - streams song-change events to browser."""
    event_bus = _get_event_bus(request)

    async def event_generator():
        queue = event_bus.subscribe()
        try:
            yield "event: connected\ndata: ok\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: song-change\ndata: {event.song_id}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/live/song/{song_id}", response_class=HTMLResponse)
async def live_song_partial(request: Request, song_id: str):
    """Render song partial for live view (no edit/delete buttons)."""
    storage = get_storage()
    templates = get_templates()
    song = storage.get_song(song_id)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    devices = storage.get_devices()
    devices_map = {d.id: d for d in devices}

    return templates.TemplateResponse(
        request=request,
        name="partials/live_song.html",
        context={"song": song, "devices": devices, "devices_map": devices_map},
    )
