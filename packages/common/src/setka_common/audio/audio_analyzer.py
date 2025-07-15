# ABOUTME: Audio analysis module for extracting beat, tempo and energy data
# ABOUTME: Provides animation timing data for Blender VSE projects

"""Audio analyzer for extracting rhythm and energy data for animations."""

import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


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
        y, sr = self.librosa.load(str(audio_path), sr=None)
        duration = len(y) / sr

        # Basic info
        result = {
            "duration": float(duration),
            "sample_rate": int(sr),
            "animation_events": {},
        }

        # Beat tracking
        tempo, beats = self.librosa.beat.beat_track(y=y, sr=sr, units="time")
        tempo_value = float(np.asarray(tempo).item())

        result["tempo"] = {
            "bpm": tempo_value,
            "beat_times": beats.tolist(),
            "beat_count": len(beats),
        }

        # Generate beat-based events
        beat_events = [
            beats[i] for i in range(0, len(beats), beat_division) if i < len(beats)
        ]
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
        result["animation_events"]["onsets"] = filtered_onsets

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

        # Detect boundaries (max 10 segments)
        boundaries_frames = self.librosa.segment.agglomerative(features, k=10)
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
        # Compute spectrogram
        S = np.abs(self.librosa.stft(y))
        freqs = self.librosa.fft_frequencies(sr=sr)

        # Define frequency bands
        bass_idx = (freqs >= 20) & (freqs <= 250)
        mid_idx = (freqs >= 250) & (freqs <= 4000)
        high_idx = (freqs >= 4000) & (freqs <= 20000)

        # Calculate energy in each band
        bass_energy = np.mean(S[bass_idx, :], axis=0)
        mid_energy = np.mean(S[mid_idx, :], axis=0)
        high_energy = np.mean(S[high_idx, :], axis=0)

        # Get time axis
        times = self.librosa.frames_to_time(np.arange(len(bass_energy)), sr=sr)

        return {
            "times": times.tolist(),
            "bass_energy": bass_energy.tolist(),
            "mid_energy": mid_energy.tolist(),
            "high_energy": high_energy.tolist(),
        }

    def _find_bass_peaks(
        self, times: List[float], bass_energy: List[float]
    ) -> List[float]:
        """Find peaks in bass energy for impact events."""
        bass_array = np.array(bass_energy)

        # Find peaks above 75th percentile
        peaks, _ = self.scipy(
            bass_array,
            height=np.percentile(bass_array, 75),
            distance=int(2.0 * len(times) / times[-1]),  # ~2 second minimum
        )

        return [times[peak] for peak in peaks]

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
