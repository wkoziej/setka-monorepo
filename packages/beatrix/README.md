# Beatrix - Audio Analysis for Setka

Audio analysis package for the Setka media processing pipeline.

## Features

- Beat detection and tempo analysis
- Energy analysis across frequency bands
- Structural audio segmentation
- Audio file validation
- CLI interface for audio analysis

## Installation

```bash
# From monorepo root
uv sync
```

## Usage

### CLI
```bash
# Analyze audio file
beatrix analyze path/to/audio.m4a

# Analyze with custom output directory
beatrix analyze path/to/audio.m4a --output-dir ./analysis/
```

### Python API
```python
from beatrix import AudioAnalyzer

analyzer = AudioAnalyzer()
result = analyzer.analyze_audio("path/to/audio.m4a")
```

## Testing

```bash
# Run tests
uv run --package beatrix --group dev pytest

# With coverage
uv run --package beatrix --group dev pytest --cov=src/beatrix
```

## Integration with Setka Packages

- **cinemon**: Uses `AudioValidator` for audio file detection and `analyze_audio_command` for automatic analysis
- **setka-common**: Provides file structure management utilities

## Dependencies

- `librosa>=0.10.0` - Audio analysis and processing
- `numpy>=1.21.0` - Numerical computations
- `scipy>=1.7.0` - Signal processing and peak detection
- `setka-common` - Shared utilities for file management