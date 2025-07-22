"""
CLI commands for Medusa.

Provides Click-based command interface for video uploads with proper error handling
and exit codes following Unix conventions.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import click

from .validators import validate_video_file, validate_config_file, validate_privacy_option, CLIValidationError
from ..uploaders.youtube import YouTubeUploader
from ..models import MediaMetadata, PlatformConfig
from ..utils.config import ConfigLoader
from ..exceptions import (
    MedusaError,
    AuthenticationError,
    NetworkError,
    UploadError
)


@click.command()
@click.argument('video_path', type=click.Path(exists=True, readable=True))
@click.option('--config', required=True, type=click.Path(exists=True, readable=True),
              help='Path to Medusa configuration JSON file')
@click.option('--title', help='Video title (auto-generated if not provided)')
@click.option('--description', help='Video description')
@click.option('--privacy', default='private', 
              type=click.Choice(['private', 'unlisted', 'public']),
              help='Privacy setting for the video')
@click.option('--tags', help='Comma-separated tags for the video')
def upload_command(video_path: str, config: str, title: Optional[str], 
                  description: Optional[str], privacy: str, tags: Optional[str]):
    """Upload video to YouTube using Medusa."""
    
    try:
        # Validate inputs
        validate_video_file(video_path)
        validate_config_file(config)
        validate_privacy_option(privacy)
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Generate default title if not provided
        if not title:
            video_name = Path(video_path).stem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            title = f"{video_name}_{timestamp}"
        
        # Generate default description if not provided
        if not description:
            description = "Uploaded via Medusa"
        
        # Create metadata
        metadata = MediaMetadata(
            title=title,
            description=description,
            privacy=privacy,
            tags=tag_list
        )
        
        # Run async upload
        result = asyncio.run(upload_video_async(video_path, config, metadata))
        
        if result.success:
            click.echo(f"✅ Upload successful: {result.media_url}")
            sys.exit(0)
        else:
            click.echo(f"❌ Upload failed: {result.error}", err=True)
            sys.exit(1)
            
    except CLIValidationError as e:
        click.echo(f"❌ Validation error: {e}", err=True)
        sys.exit(1)
    except AuthenticationError as e:
        click.echo(f"❌ Authentication failed: {e}", err=True)
        sys.exit(3)
    except NetworkError as e:
        click.echo(f"❌ Network error: {e}", err=True)
        sys.exit(4)
    except Exception as e:
        click.echo(f"❌ Upload failed: {e}", err=True)
        sys.exit(1)


async def upload_video_async(video_path: str, config_path: str, metadata: MediaMetadata):
    """
    Async function to upload video to YouTube.
    
    Args:
        video_path: Path to the video file
        config_path: Path to the configuration file
        metadata: Video metadata
        
    Returns:
        UploadResult with upload information
        
    Raises:
        AuthenticationError: If authentication fails
        Various other exceptions for different error scenarios
    """
    # Load configuration
    config_loader = ConfigLoader(config_path)
    medusa_config = config_loader.load()
    
    # Get YouTube configuration
    youtube_config = medusa_config.get_platform_config('youtube')
    if not youtube_config:
        raise AuthenticationError("YouTube configuration not found in config file", platform="youtube")
    
    # Create platform config for YouTubeUploader
    platform_config = PlatformConfig(
        platform_name="youtube",
        credentials=youtube_config.credentials if hasattr(youtube_config, 'credentials') else {}
    )
    
    # Create and configure uploader
    uploader = YouTubeUploader(config=platform_config)
    
    try:
        # Authenticate
        auth_success = await uploader.authenticate()
        if not auth_success:
            raise AuthenticationError("YouTube authentication failed", platform="youtube")
        
        # Upload video
        result = await uploader.upload_media(video_path, metadata)
        return result
        
    finally:
        # Cleanup
        if hasattr(uploader, 'cleanup'):
            await uploader.cleanup()


# Legacy function for backward compatibility
def upload():
    """Legacy upload function stub."""
    pass 