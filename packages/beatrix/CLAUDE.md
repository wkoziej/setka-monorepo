# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Beatrix is a specialized audio analysis package within the Setka monorepo that provides audio processing capabilities for animation timing and beat detection. It extracts rhythm and energy data from audio files to drive automated animations in Blender VSE projects.

## Development Commands

### Installation and Setup
```bash
# From monorepo root - install all dependencies
uv sync

# Install dev dependencies for beatrix
uv sync --group dev
```

### Testing
```bash
# Run all tests with coverage (from beatrix package directory)
uv run --group dev pytest

# Run tests from monorepo root
uv run --package beatrix pytest

# Run specific test file
uv run --group dev pytest tests/test_audio_analyzer.py -v

# Run tests with specific markers
uv run --group dev pytest -m "unit" -v
uv run --group dev pytest -m "integration" -v
uv run --group dev pytest -m "audio" -v

# Run single test
uv run --group dev pytest -k "test_analyze_for_animation" -v
```

### Development Workflow
```bash
# CLI command (installed as script entry point)
beatrix audio.m4a analysis/

# Module execution (alternative)
uv run python -m beatrix.cli.analyze_audio audio.m4a analysis/

# Python API usage
uv run python -c "from beatrix import AudioAnalyzer; analyzer = AudioAnalyzer(); result = analyzer.analyze_for_animation('audio.m4a')"
```

## Architecture Overview

### Core Components

**AudioAnalyzer** (`src/beatrix/core/audio_analyzer.py`)
- Main analysis engine using librosa for audio processing
- Lazy loading pattern for heavy dependencies (librosa, scipy)
- Extracts beats, tempo, energy bands, structural sections, and onsets
- Configurable analysis parameters (`beat_division`, `min_onset_interval`)

**AudioValidator** (`src/beatrix/core/audio_validator.py`)
- Handles audio file detection and validation in OBS recording extractions
- Supports multiple audio file scenarios with automatic detection
- Integrates with setka-common file type utilities

**CLI Interface** (`src/beatrix/cli/analyze_audio.py`)
- Command-line interface for audio analysis
- Entry point: `beatrix` command (defined in pyproject.toml)
- Alternative execution: `python -m beatrix.cli.analyze_audio`

### Key Design Patterns

**Lazy Loading**
Heavy dependencies (librosa, scipy) are loaded only when needed to improve startup performance:
```python
@property
def librosa(self):
    if self._librosa is None:
        import librosa
        self._librosa = librosa
    return self._librosa
```

**Exception Hierarchy**
- `BeatrixError`: Base exception
- `AudioValidationError`: File validation issues
- `NoAudioFileError`: No audio files found
- `MultipleAudioFilesError`: Multiple files without specification

### Output Format

The `analyze_for_animation` method returns a structured JSON with:
- `duration`, `sample_rate`: Basic audio properties
- `tempo`: BPM and beat timing information
- `animation_events`: Beat-synchronized events, sections, onsets, energy peaks
- `frequency_bands`: Time-series energy data for bass, mid, high frequencies

## Integration with Setka Monorepo

### Dependencies
- **setka-common**: File structure management and utilities
- **librosa**: Audio analysis and processing
- **numpy**: Numerical computations
- **scipy**: Signal processing algorithms

### Usage by Other Packages
- **cinemon**: Uses beatrix for Blender VSE animation timing
- **obsession**: May use beatrix for OBS recording analysis

### File Structure Integration
Works with standardized Setka recording structure:
```
recording_name/
├── extracted/          # Audio files (input)
└── analysis/          # JSON outputs (output)
```

## Testing Architecture

### Test Categories
- **Unit tests**: Mock-based testing of core components
- **Integration tests**: Real audio file processing
- **Audio tests**: Specific audio processing validation

### Test Configuration
- Minimum coverage: 85% (enforced by pytest)
- Coverage reports: Terminal and HTML
- Test markers: `unit`, `integration`, `audio`

### Common Test Patterns
```python
# Mock AudioAnalyzer for testing
@patch('beatrix.core.audio_analyzer.AudioAnalyzer')
def test_component(mock_analyzer):
    mock_analyzer.return_value.analyze_for_animation.return_value = {...}
```

## Common Development Tasks

### Adding New Analysis Features
1. Extend `AudioAnalyzer.analyze_for_animation()` method
2. Add new analysis parameters to method signature
3. Update CLI argument parser in `analyze_audio.py`
4. Add corresponding unit tests with mocked librosa calls
5. Update output JSON schema documentation

### Integrating with New Animation Modes
1. Analyze required timing data structure
2. Extend `animation_events` output format if needed
3. Update `beat_division` or add new configuration parameters
4. Test integration with cinemon package

### Performance Optimization
- Lazy loading pattern is already implemented for heavy imports
- Consider caching analysis results for repeated operations
- Profile librosa operations for bottlenecks

## CLI Usage Patterns

### Basic Analysis
```bash
# Analyze single audio file
beatrix audio.m4a analysis/

# With custom parameters
beatrix audio.m4a analysis/ --beat-division 4 --min-onset-interval 1.5
```

### Integration with Cinemon
```bash
# Cinemon automatically runs beatrix when needed
cinemon-blend-setup /path/to/recording --animation-mode beat-switch
```

## Key Files and Locations

- `src/beatrix/core/audio_analyzer.py`: Main analysis engine
- `src/beatrix/core/audio_validator.py`: File validation logic
- `src/beatrix/cli/analyze_audio.py`: CLI interface
- `src/beatrix/exceptions.py`: Custom exception classes
- `tests/`: Comprehensive test suite with fixtures
- `pyproject.toml`: Project configuration, dependencies, and test settings