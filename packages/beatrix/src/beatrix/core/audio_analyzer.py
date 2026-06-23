# ABOUTME: Audio analysis module for extracting beat, tempo and energy data
# ABOUTME: Provides animation timing data for Blender VSE projects

"""Audio analyzer for extracting rhythm and energy data for animations."""

import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)

# Analysis JSON contract. SCHEMA_VERSION is the authoritative version field
# (consumers validate the major). N_FFT is the real librosa.stft default; the
# STFT hop is n_fft // 4, which is what frames_to_time assumes, so HOP_LENGTH
# governs the dt between every frequency_bands sample.
SCHEMA_VERSION = "1.0"
N_FFT = 2048
HOP_LENGTH = N_FFT // 4  # 512


def _finite_floats(values: List[float]) -> List[float]:
    """Coerce to native float and drop any NaN/inf entries.

    Keeps the emitted contract free of non-finite numbers and numpy scalars so
    a plain json.dumps round-trips without surprises for downstream consumers.
    """
    out = []
    for v in values:
        f = float(v)
        if np.isfinite(f):
            out.append(f)
    return out


class AudioAnalyzer:
    """Analyzes audio files to extract rhythm and energy data for animations."""

    def __init__(self):
        """Initialize the audio analyzer."""
        self._librosa = None
        self._scipy = None

    @property
    def librosa(self):
        """Lazy load librosa."""
        if self._librosa is None:
            try:
                import librosa

                self._librosa = librosa
            except ImportError:
                raise ImportError(
                    "librosa is required for audio analysis. "
                    "Install with: pip install librosa"
                )
        return self._librosa

    @property
    def scipy(self):
        """Lazy load scipy."""
        if self._scipy is None:
            try:
                from scipy.signal import find_peaks

                self._scipy = find_peaks
            except ImportError:
                raise ImportError(
                    "scipy is required for peak detection. "
                    "Install with: pip install scipy"
                )
        return self._scipy

    def analyze_for_animation(
        self, audio_path: Path, beat_division: int = 8, min_onset_interval: float = 2.0
    ) -> Dict:
        """
        Analyze audio file for animation timing data.

        Args:
            audio_path: Path to audio file
            beat_division: Divide beats by this number for events
            min_onset_interval: Minimum seconds between onset events

        Returns:
            Dict with animation timing data
        """
        logger.info(f"Analyzing audio file: {audio_path}")

        # Load audio
        y, sr = self.librosa.load(str(audio_path), sr=None, mono=True)
        duration = len(y) / sr if sr else 0.0

        # Basic info + explicit, versioned contract metadata.
        result = {
            "schema_version": SCHEMA_VERSION,
            "hop_length": HOP_LENGTH,
            "n_fft": N_FFT,
            "duration": float(duration),
            "sample_rate": int(sr),
            "animation_events": {},
        }

        # Degenerate empty input: no samples → no rhythm, no energy, no sections.
        # Returning early avoids librosa/scipy crashes on zero-length buffers.
        if len(y) == 0:
            result["tempo"] = {"bpm": 0.0, "beat_times": [], "beat_count": 0}
            result["animation_events"] = {
                "beats": [],
                "sections": [],
                "onsets": [],
                "energy_peaks": [],
            }
            result["frequency_bands"] = {
                "times": [],
                "bass_energy": [],
                "mid_energy": [],
                "high_energy": [],
            }
            return result

        # Beat tracking
        tempo, beats = self.librosa.beat.beat_track(y=y, sr=sr, units="time")
        tempo_value = float(np.asarray(tempo).item())

        result["tempo"] = {
            "bpm": tempo_value,
            "beat_times": beats.tolist(),
            "beat_count": len(beats),
        }

        # Generate beat-based events. range(0, len(beats), ...) keeps every
        # index in-bounds, but beats[i] yields np.float64 — coerce to native
        # float (and drop any non-finite) for a clean JSON contract.
        beat_events = _finite_floats(
            [beats[i] for i in range(0, len(beats), beat_division)]
        )
        result["animation_events"]["beats"] = beat_events

        # Structure boundaries
        logger.info("Detecting structural boundaries...")
        boundaries = self._detect_boundaries(y, sr)
        sections = self._convert_boundaries_to_sections(boundaries)
        result["animation_events"]["sections"] = sections

        # Onset detection (filtered)
        logger.info("Detecting onsets...")
        onsets = self.librosa.onset.onset_detect(y=y, sr=sr, units="time")
        filtered_onsets = self._filter_onsets(onsets, min_onset_interval)
        result["animation_events"]["onsets"] = _finite_floats(filtered_onsets)

        # Frequency band energy
        logger.info("Analyzing frequency bands...")
        band_data = self._analyze_frequency_bands(y, sr)
        result["frequency_bands"] = band_data

        # Bass peaks for energy events
        bass_peaks = self._find_bass_peaks(band_data["times"], band_data["bass_energy"])
        result["animation_events"]["energy_peaks"] = bass_peaks

        return result

    def _detect_boundaries(self, y: np.ndarray, sr: int) -> List[float]:
        """Detect structural boundaries in audio."""
        # Compute features
        chroma = self.librosa.feature.chroma_stft(y=y, sr=sr)
        mfcc = self.librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        contrast = self.librosa.feature.spectral_contrast(y=y, sr=sr)

        # Stack features
        features = np.vstack([chroma, mfcc, contrast])

        # Agglomerative clustering needs at least 2 frames and cannot request
        # more clusters than frames; short clips would otherwise crash here
        # before reaching the rest of the pipeline.
        n_frames = features.shape[1]
        if n_frames < 2:
            return []
        k = min(10, n_frames)

        # Detect boundaries (max 10 segments)
        boundaries_frames = self.librosa.segment.agglomerative(features, k=k)
        boundaries_times = self.librosa.frames_to_time(boundaries_frames, sr=sr)

        return boundaries_times.tolist()

    def _filter_onsets(self, onsets: np.ndarray, min_interval: float) -> List[float]:
        """Filter onsets to have minimum interval between them."""
        filtered = []
        last_time = -min_interval

        for onset in onsets:
            if onset - last_time >= min_interval:
                filtered.append(float(onset))
                last_time = onset

        return filtered

    def _analyze_frequency_bands(
        self, y: np.ndarray, sr: int
    ) -> Dict[str, List[float]]:
        """Analyze energy in frequency bands over time."""
        # Compute spectrogram with the contract's STFT parameters so the
        # emitted hop_length/n_fft actually govern the dt between frames.
        S = np.abs(self.librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH))
        freqs = self.librosa.fft_frequencies(sr=sr, n_fft=N_FFT)

        # Define frequency bands
        bass_idx = (freqs >= 20) & (freqs <= 250)
        mid_idx = (freqs >= 250) & (freqs <= 4000)
        high_idx = (freqs >= 4000) & (freqs <= 20000)

        # Calculate energy in each band
        bass_energy = np.mean(S[bass_idx, :], axis=0)
        mid_energy = np.mean(S[mid_idx, :], axis=0)
        high_energy = np.mean(S[high_idx, :], axis=0)

        # Get time axis (hop_length must match the STFT hop used above)
        times = self.librosa.frames_to_time(
            np.arange(len(bass_energy)), sr=sr, hop_length=HOP_LENGTH
        )

        # A non-empty signal must produce at least one analysis frame. Zero
        # frames here means the band computation is broken, not a short clip
        # (those still yield >=1 frame); fail loudly rather than emit garbage.
        if len(times) == 0:
            raise ValueError(
                "Frequency-band analysis produced no frames for non-empty audio; "
                f"got {len(y)} samples at {sr} Hz."
            )

        return {
            "times": _finite_floats(times.tolist()),
            "bass_energy": _finite_floats(bass_energy.tolist()),
            "mid_energy": _finite_floats(mid_energy.tolist()),
            "high_energy": _finite_floats(high_energy.tolist()),
        }

    def _find_bass_peaks(
        self, times: List[float], bass_energy: List[float]
    ) -> List[float]:
        """Find peaks in bass energy for impact events."""
        # Short/empty or zero-duration input: the distance computation below
        # divides by times[-1], so guard against len<2 (no span) and a
        # non-positive final timestamp (OverflowError on int(2/0)).
        if len(times) < 2 or times[-1] <= 0:
            return []

        bass_array = np.array(bass_energy)

        # Silent-but-long input: an all-(near-)zero band makes the 75th
        # percentile 0, so find_peaks(height=0) would flag noise/every flat
        # sample as an "impact". Treat a near-silent band as no peaks.
        if bass_array.size == 0 or float(np.max(bass_array)) < 1e-6:
            return []

        # ~2 second minimum spacing; clamp to >=1 so a coarse time axis
        # (few frames over a long span) never yields distance=0.
        distance = max(1, int(2.0 * len(times) / times[-1]))

        # Find peaks above 75th percentile
        peaks, _ = self.scipy(
            bass_array,
            height=np.percentile(bass_array, 75),
            distance=distance,
        )

        return _finite_floats([times[peak] for peak in peaks])

    def _convert_boundaries_to_sections(self, boundaries: List[float]) -> List[Dict]:
        """
        Convert section boundaries to section objects.

        Args:
            boundaries: List of section boundary timestamps

        Returns:
            List of section objects with start, end, and label
        """
        if not boundaries or len(boundaries) < 2:
            return []

        sections = []
        for i in range(len(boundaries) - 1):
            sections.append(
                {
                    "start": boundaries[i],
                    "end": boundaries[i + 1],
                    "label": f"section_{i + 1}",
                }
            )

        return sections

    def save_analysis(self, analysis: Dict, output_path: Path) -> None:
        """Save analysis results to JSON file."""
        with open(output_path, "w") as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Saved audio analysis to: {output_path}")
