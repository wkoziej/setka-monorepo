#!/usr/bin/env python3
# ABOUTME: Script to generate test audio files for integration testing
# ABOUTME: Creates various audio samples with known characteristics

"""Generate test audio files for AudioAnalyzer testing."""

import numpy as np
import os
from pathlib import Path


def generate_sine_wave(frequency, duration, sample_rate=44100, amplitude=0.5):
    """Generate a sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return amplitude * np.sin(2 * np.pi * frequency * t)


def generate_beat_pattern(bpm, duration, sample_rate=44100):
    """Generate audio with clear beat pattern."""
    # Calculate beat interval
    beat_interval = 60.0 / bpm  # seconds per beat
    
    # Generate carrier sine wave
    carrier_freq = 440.0  # A4
    audio = generate_sine_wave(carrier_freq, duration, sample_rate, 0.3)
    
    # Create beat envelope
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    envelope = np.zeros_like(t)
    
    # Add beats
    for beat_time in np.arange(0, duration, beat_interval):
        # Create exponential decay envelope for each beat
        beat_mask = t >= beat_time
        beat_env = np.exp(-10 * (t - beat_time)) * beat_mask
        envelope += beat_env
    
    # Normalize envelope
    envelope = np.clip(envelope, 0, 1)
    
    # Apply envelope to carrier
    return audio * envelope


def generate_multi_section_audio(duration=10.0, sample_rate=44100):
    """Generate audio with multiple distinct sections."""
    samples = int(sample_rate * duration)
    audio = np.zeros(samples)
    
    # Section 1: 0-3s - Low frequency sine (bass)
    section1_end = int(3 * sample_rate)
    audio[:section1_end] = generate_sine_wave(100, 3, sample_rate, 0.5)
    
    # Section 2: 3-6s - Mid frequency with beats
    section2_start = section1_end
    section2_end = int(6 * sample_rate)
    section2_duration = 3
    audio[section2_start:section2_end] = generate_beat_pattern(120, section2_duration, sample_rate)
    
    # Section 3: 6-10s - High frequency sweep
    section3_start = section2_end
    t3 = np.linspace(0, 4, samples - section3_start, False)
    # Frequency sweep from 1000 to 2000 Hz
    freq_sweep = 1000 + 1000 * (t3 / 4)
    phase = 2 * np.pi * np.cumsum(freq_sweep) / sample_rate
    audio[section3_start:] = 0.3 * np.sin(phase)
    
    return audio


def save_audio_file(audio, filename, sample_rate=44100):
    """Save audio to WAV file using built-in wave module."""
    import wave
    import struct
    
    # Normalize to 16-bit range
    audio_normalized = np.int16(audio / np.max(np.abs(audio)) * 32767)
    
    # Create output directory
    output_dir = Path(__file__).parent
    output_path = output_dir / filename
    
    # Write WAV file
    with wave.open(str(output_path), 'wb') as wav_file:
        # Set parameters: 1 channel, 2 bytes per sample, sample rate
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Convert to bytes
        audio_bytes = struct.pack('h' * len(audio_normalized), *audio_normalized)
        wav_file.writeframes(audio_bytes)
    
    print(f"Generated: {output_path}")
    return output_path


def main():
    """Generate all test audio files."""
    print("Generating test audio files...")
    
    # 1. Simple sine wave (1 second)
    sine = generate_sine_wave(440, 1.0)
    save_audio_file(sine, "sine_440hz_1s.wav")
    
    # 2. Beat pattern at 120 BPM (5 seconds)
    beats = generate_beat_pattern(120, 5.0)
    save_audio_file(beats, "beats_120bpm_5s.wav")
    
    # 3. Multi-section audio (10 seconds)
    multi = generate_multi_section_audio(10.0)
    save_audio_file(multi, "multi_section_10s.wav")
    
    # 4. Short audio for quick tests (0.5 seconds)
    short = generate_beat_pattern(120, 0.5)
    save_audio_file(short, "short_beat_500ms.wav")
    
    print("\nTest audio files generated successfully!")
    print("\nFile characteristics:")
    print("- sine_440hz_1s.wav: Pure 440Hz tone, 1 second")
    print("- beats_120bpm_5s.wav: Clear beat pattern at 120 BPM, 5 seconds")
    print("- multi_section_10s.wav: 3 distinct sections (bass/beats/sweep), 10 seconds")
    print("- short_beat_500ms.wav: Quick test file, 0.5 seconds")


if __name__ == "__main__":
    main()