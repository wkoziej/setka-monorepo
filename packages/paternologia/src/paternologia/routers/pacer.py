# ABOUTME: FastAPI router for Pacer SysEx export and send endpoints.
# ABOUTME: Provides GET /pacer/export/{song_id}.syx and POST /pacer/send/{song_id}.

import logging
import subprocess
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import Response, HTMLResponse

from ..dependencies import get_storage
from ..midi.ports import find_amidi_port
from ..models import VALID_PRESETS
from ..storage import Storage
from ..pacer.export import export_song_to_syx
from ..pacer import constants as c

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pacer", tags=["pacer"])


@router.get("/export/{song_id}.syx")
def export_syx(
    song_id: str, preset: str = "A1", storage: Storage = Depends(get_storage)
):
    """Eksportuj piosenkę do .syx."""
    song = storage.get_song(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    # Walidacja preset
    if preset.upper() not in c.PRESET_INDICES:
        raise HTTPException(400, f"Invalid preset: {preset}. Valid: CURRENT, A1-D6.")

    # Pobierz devices do mapowania MIDI channels
    devices = storage.get_devices()

    syx_data = export_song_to_syx(song, devices, preset)

    return Response(
        content=syx_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{song_id}_{preset}.syx"'
        },
    )


@router.post("/send/{song_id}")
def send_to_pacer(
    request: Request,
    song_id: str,
    preset: str | None = Form(None),
    storage: Storage = Depends(get_storage),
):
    """Wyślij piosenkę do Pacera przez amidi."""
    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        song = storage.get_song(song_id)
        if not song:
            error_msg = "Song not found"
            if is_htmx:
                return HTMLResponse(
                    f'<span class="text-red-600 font-semibold">❌ {error_msg}</span>'
                )
            raise HTTPException(404, error_msg)

        target = preset or song.song.pacer_export.target_preset
        target = target.upper()

        if target not in VALID_PRESETS:
            error_msg = f"Invalid preset: {target}. Valid: A1-D6."
            if is_htmx:
                return HTMLResponse(
                    f'<span class="text-red-600 font-semibold">❌ {error_msg}</span>'
                )
            raise HTTPException(400, error_msg)

        pacer_config = storage.get_pacer_config()
        if not pacer_config:
            error_msg = "Missing configuration in data/pacer.yaml"
            if is_htmx:
                return HTMLResponse(
                    f'<span class="text-red-600 font-semibold">❌ {error_msg}</span>'
                )
            raise HTTPException(400, error_msg)

        # Auto-detekcja portu po nazwie urządzenia
        port = find_amidi_port(pacer_config.device_name)
        if not port:
            error_msg = (
                f"Nie znaleziono urządzenia '{pacer_config.device_name}'. "
                "Sprawdź połączenie i uruchom 'amidi -l'."
            )
            if is_htmx:
                return HTMLResponse(
                    f'<span class="text-red-600 font-semibold">❌ {error_msg}</span>'
                )
            raise HTTPException(400, error_msg)

        timeout_seconds = pacer_config.amidi_timeout_seconds
        sysex_interval = pacer_config.sysex_interval_ms

        devices = storage.get_devices()
        syx_data = export_song_to_syx(song, devices, target)

        try:
            with NamedTemporaryFile(suffix=".syx", delete=True) as tmp:
                tmp.write(syx_data)
                tmp.flush()
                # CRITICAL: --sysex-interval is required for reliable transfer!
                run = subprocess.run(
                    [
                        "amidi",
                        "-p",
                        port,
                        f"--sysex-interval={sysex_interval}",
                        "-s",
                        tmp.name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
        except FileNotFoundError:
            error_msg = "amidi not found - install alsa-utils package"
            if is_htmx:
                return HTMLResponse(
                    f'<span class="text-red-600 font-semibold">❌ {error_msg}</span>'
                )
            raise HTTPException(500, error_msg)

        if run.returncode != 0:
            error_msg = run.stderr.strip()
            logger.error(f"amidi failed for {song_id} to {target}: {error_msg}")
            if is_htmx:
                return HTMLResponse(
                    f'<span class="text-red-600 font-semibold">❌ Błąd wysyłania: {error_msg}</span>'
                )
            raise HTTPException(500, f"amidi failed: {error_msg}")

        # Success
        if is_htmx:
            return HTMLResponse(
                f'<span class="text-green-600">✓ Wysłano do preset {target} na port {port}</span>'
            )
        return {"status": "ok", "preset": target, "port": port}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_to_pacer: {e}", exc_info=True)
        error_msg = str(e)
        if is_htmx:
            return HTMLResponse(
                f'<span class="text-red-600 font-semibold">❌ Błąd: {error_msg}</span>'
            )
        raise HTTPException(500, f"Internal error: {error_msg}")
