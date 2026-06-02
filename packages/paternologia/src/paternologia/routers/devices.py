# ABOUTME: Devices API router for Paternologia.
# ABOUTME: Provides endpoints for listing MIDI devices and their configurations.

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from paternologia.dependencies import get_storage, get_templates

router = APIRouter(tags=["devices"])


@router.get("/devices", response_class=HTMLResponse)
async def list_devices(request: Request):
    """List all devices (HTML page)."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="devices.html",
        context={"devices": devices},
    )


@router.get("/api/devices", response_class=JSONResponse)
async def get_devices_json():
    """Get all devices as JSON (for forms/HTMX)."""
    storage = get_storage()
    devices = storage.get_devices()

    return [device.model_dump() for device in devices]
