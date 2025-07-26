"""
ABOUTME: Configuration validation utilities for setka-common config module.
ABOUTME: Provides shared validation utilities for configuration files across the monorepo.
"""

from typing import List
from pathlib import Path


class ConfigValidator:
    """Shared validation utilities for configuration files."""
    
    def validate_file_exists(self, path: Path) -> bool:
        """Validate that a file exists."""
        return path.exists() and path.is_file()
    
    def validate_range(self, value: float, min_val: float, max_val: float) -> bool:
        """Validate that a value is within range."""
        return min_val <= value <= max_val
    
    def validate_strip_targeting(self, target_strips: List[str], available_strips: List[str]) -> List[str]:
        """Validate that target strips exist in available strips."""
        missing_strips = []
        for strip in target_strips:
            if strip not in available_strips:
                missing_strips.append(strip)
        return missing_strips