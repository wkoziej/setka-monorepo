"""
Extractor functionality for OBS Canvas Recording.
This module handles video source extraction from canvas recordings.
"""

import subprocess
from typing import List, Optional, Dict, Any
from pathlib import Path

from setka_common import sanitize_filename
from setka_common.file_structure.specialized import RecordingStructureManager

# Hard ceiling for any single ffmpeg invocation. Mirrors the 30-minute bound
# used by ``advanced_scene_switcher_extractor.py`` so a wedged/stalled ffmpeg
# surfaces as a failed ``ExtractionResult`` instead of hanging the extraction.
FFMPEG_TIMEOUT_SECONDS = 1800


class ExtractionResult:
    """
    Result object for video extraction operations.

    Attributes:
        success: Boolean indicating if extraction was successful
        extracted_files: List of paths to extracted video files
        error_message: Optional error message if extraction failed
    """

    def __init__(
        self,
        success: bool = False,
        extracted_files: Optional[List[str]] = None,
        error_message: Optional[str] = None,
    ):
        """
        Initialize ExtractionResult.

        Args:
            success: Whether extraction was successful
            extracted_files: List of extracted file paths
            error_message: Error message if extraction failed
        """
        self.success = success
        self.extracted_files = extracted_files or []
        self.error_message = error_message

    def __str__(self) -> str:
        """String representation of ExtractionResult."""
        return (
            f"ExtractionResult(success={self.success}, "
            f"extracted_files={len(self.extracted_files)}, "
            f"error_message={self.error_message})"
        )


def calculate_crop_params(
    source_info: Dict[str, Any], canvas_size: List[int]
) -> Dict[str, int]:
    """
    Calculate crop parameters for FFmpeg based on source info.

    WAŻNE: Cropuje z CANVAS (wynikowego filmu), nie ze źródła!
    Źródła w OBS są renderowane na canvas, więc musimy cropować z canvas.

    Args:
        source_info: Source information with position and bounds
        canvas_size: Canvas dimensions [width, height]

    Returns:
        Dictionary with crop parameters (x, y, width, height) for canvas
    """
    # Extract position and bounds from source info
    position = source_info.get("position", {"x": 0, "y": 0})
    bounds = source_info.get("bounds", {})

    # Pozycja źródła na canvas. position może być pustym dict-em ({}), więc
    # czytamy obie osie defensywnie zamiast indeksowaniem (które rzucałoby KeyError).
    canvas_x = int(position.get("x", 0))
    canvas_y = int(position.get("y", 0))

    # Rozmiar źródła na canvas (po przeskalowaniu)
    if (
        bounds
        and "x" in bounds
        and "y" in bounds
        and bounds["x"] > 0
        and bounds["y"] > 0
    ):
        # Użyj bounds jako prawdziwego rozmiaru
        source_width_on_canvas = int(bounds["x"])
        source_height_on_canvas = int(bounds["y"])
    else:
        # Fallback do dimensions lub scale
        dimensions = source_info.get("dimensions", {})
        scale = source_info.get("scale", {"x": 1.0, "y": 1.0})

        source_width = dimensions.get("source_width", 1920)
        source_height = dimensions.get("source_height", 1080)

        source_width_on_canvas = int(source_width * scale["x"])
        source_height_on_canvas = int(source_height * scale["y"])

    # Oblicz widoczną część źródła na canvas
    # Jeśli źródło jest częściowo poza canvas, cropuj tylko widoczną część

    # Lewa krawędź widocznej części
    visible_left = max(0, canvas_x)
    # Prawa krawędź widocznej części
    visible_right = min(canvas_size[0], canvas_x + source_width_on_canvas)
    # Górna krawędź widocznej części
    visible_top = max(0, canvas_y)
    # Dolna krawędź widocznej części
    visible_bottom = min(canvas_size[1], canvas_y + source_height_on_canvas)

    # Rozmiar widocznej części
    visible_width = max(1, visible_right - visible_left)
    visible_height = max(1, visible_bottom - visible_top)

    # Parametry crop dla canvas
    crop_x = visible_left
    crop_y = visible_top
    crop_width = visible_width
    crop_height = visible_height

    return {"x": crop_x, "y": crop_y, "width": crop_width, "height": crop_height}


def _get_ffmpeg_base_cmd(input_file: str) -> List[str]:
    """
    Get base FFmpeg command.

    Args:
        input_file: Path to input video file

    Returns:
        Base FFmpeg command as list of strings
    """
    return ["ffmpeg", "-i", str(input_file)]


def _extract_video_source(
    input_file: str,
    output_file: Path,
    source_info: Dict[str, Any],
    canvas_size: List[int],
) -> None:
    """
    Extract video from source using FFmpeg.

    Args:
        input_file: Path to input video file
        output_file: Path to output video file
        source_info: Source information with position data
        canvas_size: Canvas dimensions

    Raises:
        subprocess.CalledProcessError: If FFmpeg command fails
        FileNotFoundError: If FFmpeg is not found
        ValueError: If source has invalid dimensions
    """
    # Calculate crop parameters
    crop_params = calculate_crop_params(source_info, canvas_size)
    crop_filter = f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']}"

    # Build FFmpeg command for video extraction
    cmd = _get_ffmpeg_base_cmd(input_file) + [
        "-filter:v",
        crop_filter,
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "fast",
        "-an",  # No audio in video files
        "-y",
        str(output_file),
    ]

    subprocess.run(
        cmd, check=True, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS
    )


def _extract_audio_source(
    input_file: str, output_file: Path, audio_stream_index: int = 0
) -> None:
    """
    Extract a single audio source's own stream using FFmpeg.

    Each ``has_audio`` source in an OBS multi-track recording owns a distinct
    audio stream. We select it with ``-map 0:a:<index>`` so every ``<source>.m4a``
    carries its own track — instead of every source receiving an identical copy
    of the full canvas mix.

    Args:
        input_file: Path to input video file
        output_file: Path to output audio file
        audio_stream_index: 0-based index of this source's audio stream within
            the recording (``-map 0:a:<index>``)

    Raises:
        subprocess.CalledProcessError: If FFmpeg command fails
        subprocess.TimeoutExpired: If FFmpeg exceeds ``FFMPEG_TIMEOUT_SECONDS``
        FileNotFoundError: If FFmpeg is not found
    """
    # Build FFmpeg command for per-source audio extraction.
    cmd = _get_ffmpeg_base_cmd(input_file) + [
        "-map",
        f"0:a:{audio_stream_index}",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-vn",  # No video in audio files
        "-y",
        str(output_file),
    ]

    subprocess.run(
        cmd, check=True, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS
    )


def extract_sources(
    video_file: str, metadata: Dict[str, Any], output_dir: Optional[str] = None
) -> ExtractionResult:
    """
    Extract individual sources from canvas recording.

    Args:
        video_file: Path to the input video file
        metadata: Recording metadata containing source positions
        output_dir: Optional custom output directory path

    Returns:
        ExtractionResult with success status and extracted files
    """
    # Validate input file exists
    if not Path(video_file).exists():
        return ExtractionResult(
            success=False, error_message=f"Video file not found: {video_file}"
        )

    # Validate metadata structure
    if not isinstance(metadata, dict):
        return ExtractionResult(
            success=False, error_message="Invalid metadata: must be a dictionary"
        )

    if "sources" not in metadata:
        return ExtractionResult(
            success=False, error_message="Invalid metadata: missing 'sources' field"
        )

    sources = metadata["sources"]

    # Handle empty sources - this is valid (no extraction needed)
    if not sources:
        return ExtractionResult(success=True, extracted_files=[])

    # Create output directory using FileStructureManager
    video_path = Path(video_file)
    if output_dir:
        output_dir_path = Path(output_dir)
    else:
        # Use FileStructureManager to determine output directory
        output_dir_path = RecordingStructureManager.get_extracted_dir(video_path)

    try:
        output_dir_path.mkdir(exist_ok=True, parents=True)
    except PermissionError:
        return ExtractionResult(
            success=False,
            error_message=f"Permission denied: Cannot create output directory {output_dir_path}",
        )
    except OSError as e:
        return ExtractionResult(
            success=False,
            error_message=f"Failed to create output directory {output_dir_path}: {e}",
        )

    # Get canvas size for crop calculations
    canvas_size = metadata.get("canvas_size", [1920, 1080])
    extracted_files = []

    # 0-based index into the recording's audio streams. Each source with
    # ``has_audio=True`` consumes the next stream (``-map 0:a:<index>``), in the
    # source iteration order (which mirrors the obs_script scene-item order).
    # ⚠️ The exact source→stream correspondence is assumed to match OBS
    # multi-track output ordering; it must be validated against a real
    # recording's metadata.json + .mkv (see Unit 5.1 FLAG).
    audio_stream_index = 0

    # Process each source based on its capabilities
    for source_name, source_info in sources.items():
        has_audio = source_info.get("has_audio", False)
        has_video = source_info.get("has_video", False)

        # Skip sources without audio or video
        if not has_audio and not has_video:
            continue

        safe_source_name = sanitize_filename(source_name)

        # Extract video if source has video
        if has_video:
            # Check if source has valid dimensions before creating output file
            try:
                dimensions = source_info.get("dimensions", {})
                source_width = dimensions.get("source_width", 1920)
                source_height = dimensions.get("source_height", 1080)

                if source_width <= 0 or source_height <= 0:
                    print(
                        f"Warning: Skipping video extraction for {source_name}: Source has invalid dimensions: {source_width}x{source_height}"
                    )
                    continue

                video_output_file = output_dir_path / f"{safe_source_name}.mp4"

                _extract_video_source(
                    video_file, video_output_file, source_info, canvas_size
                )
                extracted_files.append(str(video_output_file))
            except subprocess.TimeoutExpired:
                return ExtractionResult(
                    success=False,
                    error_message=(
                        f"FFmpeg timeout ({FFMPEG_TIMEOUT_SECONDS}s) extracting "
                        f"video from {source_name}"
                    ),
                )
            except subprocess.CalledProcessError as e:
                return ExtractionResult(
                    success=False,
                    error_message=f"FFmpeg failed to extract video from {source_name}: {e.stderr}",
                )
            except FileNotFoundError:
                return ExtractionResult(
                    success=False,
                    error_message="FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.",
                )

        # Extract audio if source has audio
        if has_audio:
            audio_output_file = output_dir_path / f"{safe_source_name}.m4a"

            try:
                _extract_audio_source(
                    video_file, audio_output_file, audio_stream_index
                )
                extracted_files.append(str(audio_output_file))
            except subprocess.TimeoutExpired:
                return ExtractionResult(
                    success=False,
                    error_message=(
                        f"FFmpeg timeout ({FFMPEG_TIMEOUT_SECONDS}s) extracting "
                        f"audio from {source_name}"
                    ),
                )
            except subprocess.CalledProcessError as e:
                return ExtractionResult(
                    success=False,
                    error_message=f"FFmpeg failed to extract audio from {source_name}: {e.stderr}",
                )
            except FileNotFoundError:
                return ExtractionResult(
                    success=False,
                    error_message="FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.",
                )

            # This source consumed an audio stream; advance to the next one.
            audio_stream_index += 1

    return ExtractionResult(success=True, extracted_files=extracted_files)


class SourceExtractor:
    """
    Extractor for individual sources from canvas recording.
    """

    def __init__(self, input_file: str, metadata: Dict[str, Any], output_dir: str):
        """
        Initialize SourceExtractor.

        Args:
            input_file: Path to the input video file
            metadata: Recording metadata containing source information
            output_dir: Directory to save extracted files
        """
        self.input_file = input_file
        self.metadata = metadata
        self.output_dir = output_dir

    def extract_sources(self) -> ExtractionResult:
        """
        Extract sources using the standalone function.

        Returns:
            ExtractionResult with success status and extracted files
        """
        return extract_sources(self.input_file, self.metadata, self.output_dir)
