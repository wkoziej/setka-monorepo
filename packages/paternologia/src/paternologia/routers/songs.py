# ABOUTME: Songs API router for Paternologia.
# ABOUTME: Provides CRUD endpoints for song configurations with HTMX support.

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from paternologia.dependencies import get_storage, get_templates
from paternologia.models import (
    Action,
    ActionType,
    PacerButton,
    PacerExportSettings,
    Song,
    SongMetadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["songs"])


def _rebuild_midi_index(request: Request) -> None:
    """Rebuild MIDI index after song changes (if MIDI subsystem is active)."""
    midi_index = getattr(request.app.state, "midi_index", None)
    listener = getattr(request.app.state, "midi_listener", None)
    if midi_index is None:
        return

    from paternologia.midi.index import SongMidiIndex

    storage = get_storage()
    new_index = SongMidiIndex.build(storage.get_songs(), storage.get_devices())
    request.app.state.midi_index = new_index
    if listener is not None:
        listener.song_index = new_index
    logger.info("MIDI index rebuilt")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page - list all songs."""
    storage = get_storage()
    templates = get_templates()
    songs = storage.get_songs()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"songs": songs, "devices": devices},
    )


@router.get("/songs/new", response_class=HTMLResponse)
async def new_song(request: Request):
    """Form for creating a new song."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="song_edit.html",
        context={"song": None, "devices": devices, "is_new": True},
    )


@router.get("/songs/{song_id}", response_class=HTMLResponse)
async def view_song(request: Request, song_id: str):
    """View a song's PACER configuration."""
    storage = get_storage()
    templates = get_templates()
    song = storage.get_song(song_id)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    devices = storage.get_devices()
    devices_map = {d.id: d for d in devices}

    return templates.TemplateResponse(
        request=request,
        name="song.html",
        context={"song": song, "devices": devices, "devices_map": devices_map},
    )


@router.get("/songs/{song_id}/edit", response_class=HTMLResponse)
async def edit_song(request: Request, song_id: str):
    """Form for editing a song."""
    storage = get_storage()
    templates = get_templates()
    song = storage.get_song(song_id)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="song_edit.html",
        context={"song": song, "devices": devices, "is_new": False},
    )


@router.post("/songs", response_class=HTMLResponse)
async def create_song(request: Request):
    """Create a new song from form data."""
    storage = get_storage()
    form_data = await request.form()

    song_id = form_data.get("song_id", "").strip()
    song_name = form_data.get("song_name", "").strip()
    song_author = form_data.get("song_author", "").strip()
    song_notes = form_data.get("song_notes", "").strip()

    if not song_id or not song_name:
        raise HTTPException(status_code=400, detail="ID and name are required")

    if storage.song_exists(song_id):
        raise HTTPException(status_code=400, detail="Song with this ID already exists")

    try:
        song = _build_song_from_form(
            form_data, song_id, song_name, song_author, song_notes, storage
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_format_validation_error(exc))
    storage.save_song(song)
    _rebuild_midi_index(request)

    return RedirectResponse(url=f"/songs/{song_id}", status_code=303)


@router.put("/songs/{song_id}", response_class=HTMLResponse)
async def update_song(request: Request, song_id: str):
    """Update an existing song from form data."""
    storage = get_storage()

    if not storage.song_exists(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    form_data = await request.form()
    song_name = form_data.get("song_name", "").strip()
    song_author = form_data.get("song_author", "").strip()
    song_notes = form_data.get("song_notes", "").strip()

    if not song_name:
        raise HTTPException(status_code=400, detail="Name is required")

    try:
        song = _build_song_from_form(
            form_data, song_id, song_name, song_author, song_notes, storage
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_format_validation_error(exc))
    storage.save_song(song)
    _rebuild_midi_index(request)

    return RedirectResponse(url=f"/songs/{song_id}", status_code=303)


@router.post("/songs/{song_id}", response_class=HTMLResponse)
async def update_song_post(request: Request, song_id: str):
    """Update song via POST (progressive enhancement fallback for browsers without JS)."""
    return await update_song(request, song_id)


@router.delete("/songs/{song_id}")
async def delete_song(request: Request, song_id: str):
    """Delete a song."""
    storage = get_storage()

    if not storage.delete_song(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    _rebuild_midi_index(request)
    return RedirectResponse(url="/", status_code=303)


@router.get("/api/songs/order")
async def get_songs_order():
    """Get current songs order."""
    storage = get_storage()
    return storage.get_songs_order()


@router.put("/api/songs/order")
async def update_songs_order(order: list[str]):
    """Update songs order for drag & drop reordering."""
    storage = get_storage()
    storage.save_songs_order(order)
    return {"status": "ok"}


def _build_song_from_form(
    form_data,
    song_id: str,
    song_name: str,
    song_author: str,
    song_notes: str,
    storage,
) -> Song:
    """Build a Song model from form data."""
    target_preset = form_data.get("pacer_export_target_preset", "A1").strip()
    pacer_export = PacerExportSettings(target_preset=target_preset or "A1")

    pacer_buttons = []
    button_idx = 0

    while True:
        button_name = form_data.get(f"button_{button_idx}_name", "").strip()
        if not button_name and button_idx > 0:
            break

        if button_name:
            actions = []

            # Collect actions regardless of index gaps (handles deletion of early actions)
            for action_idx in range(6):
                action_device = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_device", ""
                ).strip()
                if not action_device:
                    continue  # Skip missing actions instead of breaking

                action_type_str = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_type", ""
                ).strip()
                action_value = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_value", ""
                ).strip()
                action_cc = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_cc", ""
                ).strip()
                action_note = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_note", ""
                ).strip()
                action_velocity = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_velocity", ""
                ).strip()
                action_label = form_data.get(
                    f"button_{button_idx}_action_{action_idx}_label", ""
                ).strip()

                if action_type_str:
                    action_type = ActionType(action_type_str)

                    value = None
                    if action_value:
                        if action_type == ActionType.PATTERN:
                            value = action_value
                        else:
                            value = int(action_value)

                    action = Action(
                        device=action_device,
                        type=action_type,
                        value=value,
                        cc=int(action_cc) if action_cc else None,
                        note=action_note or None,
                        velocity=int(action_velocity) if action_velocity else None,
                        label=action_label or None,
                    )
                    actions.append(action)

            pacer_buttons.append(PacerButton(name=button_name, actions=actions))

        button_idx += 1
        if button_idx > 6:
            break

    return Song(
        song=SongMetadata(
            id=song_id,
            name=song_name,
            author=song_author,
            created=date.today(),
            notes=song_notes,
            pacer_export=pacer_export,
        ),
        pacer=pacer_buttons,
    )


def _format_validation_error(exc: ValidationError) -> str:
    """Build a short validation error message for HTTP responses."""
    if not exc.errors():
        return "Niepoprawne dane formularza."
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first.get("loc", []))
    msg = first.get("msg", "Niepoprawne dane formularza.")
    if loc:
        return f"{loc}: {msg}"
    return msg


@router.get("/partials/action-row", response_class=HTMLResponse)
async def get_action_row(request: Request, button_idx: int, action_idx: int):
    """Return a new action row partial for HTMX."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="partials/action_row.html",
        context={
            "button_idx": button_idx,
            "action_idx": action_idx,
            "action": None,
            "devices": devices,
        },
    )


@router.get("/partials/pacer-button", response_class=HTMLResponse)
async def get_pacer_button(request: Request, button_idx: int):
    """Return a new PACER button partial for HTMX."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="partials/pacer_button.html",
        context={
            "button_idx": button_idx,
            "button": None,
            "devices": devices,
            "is_edit": True,
        },
    )


@router.get("/partials/action-types", response_class=HTMLResponse)
async def get_action_types(
    request: Request, device_id: str, button_idx: int, action_idx: int
):
    """Return action type options for selected device (HTMX cascade)."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    device = next((d for d in devices if d.id == device_id), None)
    action_types = device.action_types if device else []

    return templates.TemplateResponse(
        request=request,
        name="partials/action_types.html",
        context={
            "button_idx": button_idx,
            "action_idx": action_idx,
            "action_types": action_types,
        },
    )


@router.get("/partials/action-fields", response_class=HTMLResponse)
async def get_action_fields(
    request: Request, action_type: str, button_idx: int, action_idx: int
):
    """Return input fields for selected action type (HTMX cascade)."""
    templates = get_templates()

    return templates.TemplateResponse(
        request=request,
        name="partials/action_fields.html",
        context={
            "button_idx": button_idx,
            "action_idx": action_idx,
            "action_type": action_type,
            "action": None,
        },
    )
