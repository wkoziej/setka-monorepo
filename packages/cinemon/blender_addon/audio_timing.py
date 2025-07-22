# ABOUTME: Audio timing management for Cinemon animations
# ABOUTME: Converts beatrix analysis data into keyframe timing for Blender animations

"""Audio timing support for Cinemon animations.

This module provides functionality to convert beatrix audio analysis data
into precise timing for Blender keyframes, replacing fixed intervals with
real audio-driven events.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AudioTimingManager:
    """Manages audio timing data for animations."""
    
    def __init__(self):
        """Initialize the audio timing manager."""
        self._audio_data = None
        self._fps = 30  # Default FPS
        
    def set_audio_data(self, audio_analysis_data: Optional[Dict[str, Any]]):
        """Set audio analysis data for timing calculations.
        
        Args:
            audio_analysis_data: Beatrix audio analysis data with animation_events
        """
        self._audio_data = audio_analysis_data
        if audio_analysis_data and 'animation_events' in audio_analysis_data:
            events = audio_analysis_data['animation_events']
            beat_count = len(events.get('beats', []))
            energy_count = len(events.get('energy_peaks', []))
            sections_count = len(events.get('sections', []))
            logger.info(f"Audio timing loaded: {beat_count} beats, {energy_count} energy peaks, {sections_count} sections")
    
    def set_fps(self, fps: int):
        """Set project FPS for frame calculations.
        
        Args:
            fps: Frames per second for the project
        """
        self._fps = fps
    
    def get_event_frames(self, trigger: str) -> List[int]:
        """Get frame numbers for a specific trigger type.
        
        Args:
            trigger: Animation trigger type ('beat', 'bass', 'energy_peaks', 'sections')
            
        Returns:
            List of frame numbers where events occur
        """
        if not self._audio_data or 'animation_events' not in self._audio_data:
            logger.warning(f"No audio data available for trigger '{trigger}', using fallback")
            return self._get_fallback_frames(trigger)
        
        events = self._audio_data['animation_events']
        
        # Map trigger names to event types
        trigger_map = {
            'beat': 'beats',
            'bass': 'energy_peaks',
            'energy_peaks': 'energy_peaks',
            'sections': 'sections'
        }
        
        event_type = trigger_map.get(trigger, 'beats')
        timestamps = events.get(event_type, [])
        
        if not timestamps:
            logger.warning(f"No {event_type} events found, using fallback")
            return self._get_fallback_frames(trigger)
        
        # Convert timestamps to frame numbers
        frames = []
        for timestamp in timestamps:
            if isinstance(timestamp, dict):
                # Section format: {"start": float, "end": float, "label": string}
                frame = int(timestamp.get('start', 0) * self._fps)
            else:
                # Simple timestamp format
                frame = int(timestamp * self._fps)
            
            if frame >= 0:
                frames.append(frame)
        
        logger.info(f"Converted {len(timestamps)} {event_type} events to frames: {frames[:5]}{'...' if len(frames) > 5 else ''}")
        return frames
    
    def _get_fallback_frames(self, trigger: str) -> List[int]:
        """Get fallback frame timing when no audio data is available.
        
        Args:
            trigger: Animation trigger type
            
        Returns:
            List of frame numbers using fixed intervals
        """
        # Default timeline range (should come from Blender context)
        try:
            import bpy
            frame_start = bpy.context.scene.frame_start
            frame_end = bpy.context.scene.frame_end
        except:
            frame_start, frame_end = 1, 250
        
        # Fixed intervals based on trigger type (legacy behavior)
        intervals = {
            'beat': 30,
            'bass': 30, 
            'energy_peaks': 60,
            'sections': 120
        }
        
        interval = intervals.get(trigger, 45)
        frames = list(range(frame_start, frame_end + 1, interval))
        
        logger.info(f"Using fallback timing for '{trigger}': interval={interval}, frames={len(frames)}")
        return frames
    
    def get_keyframe_timing(self, trigger: str, duration_frames: int = 3) -> List[Dict[str, int]]:
        """Get keyframe timing data for animations.
        
        Args:
            trigger: Animation trigger type
            duration_frames: Duration of animation in frames
            
        Returns:
            List of dicts with 'start' and 'end' frame numbers
        """
        event_frames = self.get_event_frames(trigger)
        
        keyframes = []
        for frame in event_frames:
            keyframes.append({
                'start': frame,
                'end': frame + duration_frames
            })
        
        return keyframes
    
    def has_audio_data(self) -> bool:
        """Check if audio timing data is available.
        
        Returns:
            True if audio data is loaded and valid
        """
        return (self._audio_data is not None and 
                'animation_events' in self._audio_data and
                bool(self._audio_data['animation_events']))


# Global instance for use throughout the addon
_audio_timing_manager = None


def get_audio_timing_manager() -> AudioTimingManager:
    """Get the global audio timing manager instance.
    
    Returns:
        AudioTimingManager: Global instance
    """
    global _audio_timing_manager
    if _audio_timing_manager is None:
        _audio_timing_manager = AudioTimingManager()
    return _audio_timing_manager


def set_global_audio_data(audio_analysis_data: Optional[Dict[str, Any]]):
    """Set audio data on the global timing manager.
    
    Args:
        audio_analysis_data: Beatrix audio analysis data
    """
    manager = get_audio_timing_manager()
    manager.set_audio_data(audio_analysis_data)


def set_global_fps(fps: int):
    """Set FPS on the global timing manager.
    
    Args:
        fps: Project frames per second
    """
    manager = get_audio_timing_manager()
    manager.set_fps(fps)