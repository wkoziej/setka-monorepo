#!/usr/bin/env python3
# ABOUTME: Demo script showing audio analysis output for animation
# ABOUTME: Generates sample analysis and visualizes the data structure

"""Demo script to show audio analysis output."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from beatrix import AudioAnalyzer


def format_time_list(times, max_items=5):
    """Format time list for display."""
    if len(times) <= max_items:
        return [f"{t:.2f}s" for t in times]
    else:
        formatted = [f"{t:.2f}s" for t in times[:max_items]]
        formatted.append(f"... (+{len(times) - max_items} more)")
        return formatted


def demo_analysis(audio_file: Path):
    """Run demo analysis and display results."""
    print(f"\n{'=' * 60}")
    print(f"Audio Analysis Demo: {audio_file.name}")
    print(f"{'=' * 60}\n")

    # Create analyzer
    analyzer = AudioAnalyzer()

    # Run analysis
    print("🎵 Analyzing audio file...")
    result = analyzer.analyze_for_animation(
        audio_file,
        beat_division=8,  # For PiP switching every 8 beats
        min_onset_interval=1.5,  # Filter close onsets
    )

    # Display results
    print("\n📊 Basic Info:")
    print(f"  Duration: {result['duration']:.2f} seconds")
    print(f"  Sample Rate: {result['sample_rate']} Hz")
    print(f"  Tempo: {result['tempo']['bpm']:.1f} BPM")
    print(f"  Total Beats: {result['tempo']['beat_count']}")

    print("\n🎬 Animation Events:")
    events = result["animation_events"]

    print(f"  Beat Switch Events (every 8 beats): {len(events['beats'])}")
    print(f"    Times: {format_time_list(events['beats'])}")

    print(f"\n  Section Boundaries: {len(events['sections'])}")
    print(f"    Times: {format_time_list(events['sections'])}")

    print(f"\n  Filtered Onsets: {len(events['onsets'])}")
    print(f"    Times: {format_time_list(events['onsets'])}")

    print(f"\n  Energy Peaks (bass): {len(events['energy_peaks'])}")
    print(f"    Times: {format_time_list(events['energy_peaks'])}")

    print("\n📈 Frequency Bands:")
    bands = result["frequency_bands"]
    print(f"  Time points: {len(bands['times'])}")
    print(f"  Update rate: ~{len(bands['times']) / result['duration']:.1f} Hz")

    # Show example energy values
    if len(bands["bass_energy"]) > 0:
        print("\n  Energy ranges:")
        print(
            f"    Bass: {min(bands['bass_energy']):.3f} - {max(bands['bass_energy']):.3f}"
        )
        print(
            f"    Mid:  {min(bands['mid_energy']):.3f} - {max(bands['mid_energy']):.3f}"
        )
        print(
            f"    High: {min(bands['high_energy']):.3f} - {max(bands['high_energy']):.3f}"
        )

    # Save example output
    output_file = audio_file.parent / f"{audio_file.stem}_analysis.json"
    analyzer.save_analysis(result, output_file)
    print(f"\n💾 Analysis saved to: {output_file}")

    # Show how this would be used in Blender
    print("\n🎨 Example Blender Animation Usage:")
    print(f"  - PiP switches at: {format_time_list(events['beats'][:3])}")
    print(f"  - Major transitions at: {format_time_list(events['sections'])}")
    print(f"  - Bass pulse peaks at: {format_time_list(events['energy_peaks'][:3])}")
    print("  - Continuous energy data for smooth animations")

    return result


def main():
    """Run demo on test audio files."""
    # Check if custom file provided
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        if not audio_file.exists():
            print(f"❌ File not found: {audio_file}")
            return
        demo_analysis(audio_file)
    else:
        # Use test fixtures
        fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "audio"

        # Demo different types
        test_files = ["beats_120bpm_5s.wav", "multi_section_10s.wav"]

        for filename in test_files:
            audio_file = fixtures_dir / filename
            if audio_file.exists():
                demo_analysis(audio_file)
            else:
                print(f"⚠️  Skipping {filename} - not found")

        print("\n💡 Tip: Run with custom audio file:")
        print(f"   python {sys.argv[0]} path/to/your/audio.wav")


if __name__ == "__main__":
    main()
