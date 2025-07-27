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
# Show help
beatrix --help

# Analyze audio file with default settings
beatrix analyze path/to/audio.m4a output_dir/

# Analyze with custom beat division
beatrix analyze path/to/audio.m4a output_dir/ --beat-division 4

# Analyze with custom onset interval
beatrix analyze path/to/audio.m4a output_dir/ --min-onset-interval 1.5

# Enable verbose output
beatrix --verbose analyze path/to/audio.m4a output_dir/
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
uv run --package beatrix --group dev pytest --cov=beatrix
```

## Integration with Setka Packages

- **cinemon**: Uses `AudioValidator` for audio file detection and `analyze_audio_command` for automatic analysis
- **setka-common**: Provides file structure management utilities

## Dependencies

- `librosa>=0.10.0` - Audio analysis and processing
- `numpy>=1.21.0` - Numerical computations
- `scipy>=1.7.0` - Signal processing and peak detection
- `setka-common` - Shared utilities for file management
- `click>=8.2.1` - Modernized CLI framework
