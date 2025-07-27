# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Setka-common is a **shared utilities package** within the Setka monorepo. It provides common functionality used by all other packages in the workspace.

## Architecture Overview

### Core Components

- **file_structure/**: Standardized directory organization utilities
  - `RecordingStructureManager`: Manages recording directory structure
  - Base classes for file structure management
- **config/**: YAML configuration system for Blender VSE projects
  - `YAMLConfigLoader`: Loads and validates YAML configuration files
  - `BlenderYAMLConfig`: Complete configuration dataclass
  - `ConfigValidationError`: Custom exception for validation errors
  - Validation constants: `VALID_ANIMATION_TYPES`, `VALID_TRIGGERS`, `VALID_LAYOUT_TYPES`
- **utils/**: General utility functions

### Configuration System

The config module provides a **single source of truth** for:
- Animation type validation
- Trigger type validation
- Layout type validation
- Type-safe configuration structures using TypedDict

This ensures consistency across all packages that need to validate YAML configurations.

### Integration with Other Packages

- **cinemon**: Imports validation constants and ConfigValidationError for blender_addon
- **obsession**: Uses RecordingStructureManager for organizing extracted files
- **beatrix**: Uses file structure utilities for analysis output
- **medusa**: Uses file structure for locating render outputs

## Common Development Commands

```bash
# Run all tests
uv run pytest packages/common/tests/

# Run specific test file
uv run pytest packages/common/tests/config/test_yaml_config.py -v

# Check imports
uv run python -c "from setka_common.config import *"
```

## Key Exports

The package exports these key components:

```python
from setka_common import (
    # File structure management
    RecordingStructureManager,

    # Configuration classes
    BlenderYAMLConfig,
    YAMLConfigLoader,
    ConfigValidator,
    AnimationSpec,
    StripAnimations,
    ConfigValidationError,
    ProjectConfig,
    AudioAnalysisConfig,
    LayoutConfig,
    Resolution,

    # Validation constants
    VALID_ANIMATION_TYPES,
    VALID_TRIGGERS,
    VALID_LAYOUT_TYPES,
)
```

## Testing

Tests are located in `packages/common/tests/` and cover:
- File structure management
- YAML configuration loading and validation
- Error handling
- Import functionality
