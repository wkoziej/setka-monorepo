# ABOUTME: Health endpoint reporting live MIDI/OBS subsystem state.
# ABOUTME: Used as an at-a-glance reliability indicator during performances.

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    """Report the real state of the MIDI bridge, PACER input, and OBS link."""
    state = request.app.state
    listener = getattr(state, "midi_listener", None)
    bridge = getattr(state, "midi_bridge", None)
    return {
        "pacer_input_open": bool(listener is not None and listener.is_active),
        "bridge_port_active": bool(bridge is not None and bridge.is_active),
        "obs_connected": bool(getattr(state, "obs_connected", False)),
        "last_heartbeat_ts": getattr(state, "last_heartbeat_ts", None),
    }
