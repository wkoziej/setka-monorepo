"""
ABOUTME: YAML configuration classes for Blender VSE project configuration.
ABOUTME: Provides dataclasses for project, audio analysis, layout, and animation specifications.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import yaml


@dataclass
class ProjectConfig:
    """Configuration for Blender VSE project parameters."""
    
    video_files: List[str]
    main_audio: Optional[str] = None
    output_blend: Optional[str] = None
    render_output: Optional[str] = None
    fps: int = 30
    resolution: Optional[Dict[str, int]] = None
    beat_division: int = 8


@dataclass
class AudioAnalysisConfig:
    """Configuration for audio analysis data."""
    
    file: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class LayoutConfig:
    """Configuration for video layout parameters."""
    
    type: str = "random"
    config: Optional[Dict[str, Any]] = None


@dataclass
class AnimationSpec:
    """Specification for individual animation with dynamic parameters."""
    
    type: str
    trigger: str
    target_strips: List[str]
    
    def __init__(self, type: str, trigger: str, target_strips: List[str], **kwargs):
        self.type = type
        self.trigger = trigger
        self.target_strips = target_strips
        
        # Store additional parameters as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class BlenderYAMLConfig:
    """Complete YAML configuration for Blender VSE project."""
    
    project: ProjectConfig
    audio_analysis: AudioAnalysisConfig
    layout: LayoutConfig
    animations: List[AnimationSpec]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return {
            'project': {
                'video_files': self.project.video_files,
                'main_audio': self.project.main_audio,
                'output_blend': self.project.output_blend,
                'render_output': self.project.render_output,
                'fps': self.project.fps,
                'resolution': self.project.resolution,
                'beat_division': self.project.beat_division
            },
            'audio_analysis': {
                'file': self.audio_analysis.file,
                'data': self.audio_analysis.data
            },
            'layout': {
                'type': self.layout.type,
                'config': self.layout.config
            },
            'animations': [
                {
                    'type': anim.type,
                    'trigger': anim.trigger,
                    'target_strips': anim.target_strips,
                    **{k: v for k, v in anim.__dict__.items() 
                       if k not in ('type', 'trigger', 'target_strips')}
                }
                for anim in self.animations
            ]
        }


class YAMLConfigLoader:
    """Loader and validator for YAML configuration files."""
    
    VALID_ANIMATION_TYPES = {
        "scale", "shake", "rotation", "jitter", "brightness_flicker",
        "black_white", "film_grain", "vintage_color"
    }
    
    VALID_TRIGGERS = {
        "bass", "beat", "energy_peaks", "one_time", "continuous"
    }
    
    VALID_LAYOUT_TYPES = {
        "random", "grid", "center", "fill"
    }
    
    def load_config(self, config_path: Path) -> BlenderYAMLConfig:
        """Load and validate YAML configuration."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")
        
        # Parse sections
        project_data = data.get("project", {})
        audio_analysis_data = data.get("audio_analysis", {})
        layout_data = data.get("layout", {})
        animations_data = data.get("animations", [])
        
        # Create configuration objects
        project = self._parse_project_config(project_data)
        audio_analysis = self._parse_audio_analysis_config(audio_analysis_data)
        layout = self._parse_layout_config(layout_data)
        animations = self._parse_animations_config(animations_data)
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        # Validate configuration
        is_valid, errors = self.validate_config(config)
        if not is_valid:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return config
    
    def _parse_project_config(self, data: Dict[str, Any]) -> ProjectConfig:
        """Parse project configuration section."""
        video_files = data.get("video_files", [])
        if not isinstance(video_files, list):
            raise ValueError("video_files must be a list")
        
        return ProjectConfig(
            video_files=video_files,
            main_audio=data.get("main_audio"),
            output_blend=data.get("output_blend"),
            render_output=data.get("render_output"),
            fps=data.get("fps", 30),
            resolution=data.get("resolution"),
            beat_division=data.get("beat_division", 8)
        )
    
    def _parse_audio_analysis_config(self, data: Dict[str, Any]) -> AudioAnalysisConfig:
        """Parse audio analysis configuration section."""
        return AudioAnalysisConfig(
            file=data.get("file"),
            data=data.get("data")
        )
    
    def _parse_layout_config(self, data: Dict[str, Any]) -> LayoutConfig:
        """Parse layout configuration section."""
        return LayoutConfig(
            type=data.get("type", "random"),
            config=data.get("config")
        )
    
    def _parse_animations_config(self, data: List[Dict[str, Any]]) -> List[AnimationSpec]:
        """Parse animations configuration section."""
        animations = []
        for anim_data in data:
            anim_type = anim_data.get("type")
            trigger = anim_data.get("trigger")
            target_strips = anim_data.get("target_strips", [])
            
            if not anim_type or not trigger:
                raise ValueError("Animation must have 'type' and 'trigger' fields")
            
            # Extract additional parameters
            kwargs = {k: v for k, v in anim_data.items() 
                     if k not in ["type", "trigger", "target_strips"]}
            
            animation = AnimationSpec(
                type=anim_type,
                trigger=trigger,
                target_strips=target_strips,
                **kwargs
            )
            animations.append(animation)
        
        return animations
    
    def validate_config(self, config: BlenderYAMLConfig) -> Tuple[bool, List[str]]:
        """Validate configuration with fail-fast approach."""
        errors = []
        
        # Validate project
        if not config.project.video_files:
            errors.append("Project must have at least one video file")
        
        if config.project.fps <= 0:
            errors.append("FPS must be greater than 0")
        
        if config.project.resolution:
            width = config.project.resolution.get("width", 0)
            height = config.project.resolution.get("height", 0)
            if width <= 0 or height <= 0:
                errors.append("Resolution width and height must be greater than 0")
        
        # Validate layout
        if config.layout.type not in self.VALID_LAYOUT_TYPES:
            errors.append(f"Invalid layout type: {config.layout.type}. Must be one of {self.VALID_LAYOUT_TYPES}")
        
        # Validate animations
        for i, animation in enumerate(config.animations):
            if animation.type not in self.VALID_ANIMATION_TYPES:
                errors.append(f"Animation {i}: Invalid type '{animation.type}'. Must be one of {self.VALID_ANIMATION_TYPES}")
            
            if animation.trigger not in self.VALID_TRIGGERS:
                errors.append(f"Animation {i}: Invalid trigger '{animation.trigger}'. Must be one of {self.VALID_TRIGGERS}")
        
        return len(errors) == 0, errors
    
