# Medusa - Media Upload & Social Automation Library

## Overview

Medusa is a Python library designed for personal automation of media uploads to hosting platforms (YouTube, Vimeo) and subsequent social media publishing (Facebook, Twitter, LinkedIn). The library provides asynchronous task processing with status tracking for reliable automation workflows.

## Core Requirements

### Primary Use Case
- Personal project for automating own publications
- Used as a library imported into other Python projects
- Web application integration with server-side media publishing

### Key Features
- Asynchronous media upload with task tracking
- Cross-platform dependency handling (YouTube upload → Facebook post with link)
- Simple status monitoring with basic states
- Fail-fast approach: stop all tasks if primary platform fails
- JSON-based configuration for credentials and settings

## API Design

### Core Interface

```python
from medusa import MedusaCore

# Initialize with config file
medusa = MedusaCore(config_file="medusa_config.json")

# Async publish with task tracking
task_id = medusa.publish_async(
    media_file="video.mp4",
    platforms=["youtube", "facebook"],
    metadata={
        "youtube": {
            "title": "My Video Title",
            "description": "Video description",
            "privacy": "unlisted",
            "tags": ["demo", "test"]
        },
        "facebook": {
            "message": "Check out my new video: {youtube_url}"
        }
    }
)

# Status checking
status = medusa.get_task_status(task_id)
```

### Task Status Response

**Successful completion:**
```json
{
    "status": "completed",
    "results": {
        "youtube_url": "https://youtube.com/watch?v=abc123",
        "facebook_post_id": "123456789"
    }
}
```

**Failure (fail-fast approach):**
```json
{
    "status": "failed",
    "error": "YouTube API error: Video file too large (max 128GB)",
    "failed_platform": "youtube"
}
```

**In progress:**
```json
{
    "status": "in_progress",
    "message": "Uploading to YouTube..."
}
```

### Task States
- `pending`: Task created, not yet started
- `in_progress`: Currently processing
- `completed`: All platforms successfully processed
- `failed`: Task stopped due to error

## Architecture

### Core Components

1. **MedusaCore**: Main interface for task management and coordination
2. **Uploaders**: Platform-specific upload handlers (YouTubeUploader, VimeoUploader)
3. **Publishers**: Social media publishing handlers (FacebookPublisher, TwitterPublisher)
4. **TaskManager**: In-memory task tracking and status management

### Platform Integration
- Built-in support for major platforms (hardcoded, no plugin system)
- Dependency resolution between platforms (YouTube link → Facebook post)
- Platform-specific error handling with API error details

## Configuration

### JSON Configuration File

```json
{
    "youtube": {
        "client_secrets_file": "secrets/youtube_client_secrets.json",
        "credentials_file": "secrets/youtube_credentials.json"
    },
    "facebook": {
        "page_id": "1234567890",
        "access_token": "your_facebook_access_token"
    },
    "vimeo": {
        "access_token": "your_vimeo_access_token"
    },
    "twitter": {
        "api_key": "your_twitter_api_key",
        "api_secret": "your_twitter_api_secret",
        "access_token": "your_twitter_access_token",
        "access_token_secret": "your_twitter_access_token_secret"
    }
}
```

## Technical Implementation

### Dependencies
- Python 3.8+
- `google-api-python-client` (YouTube)
- `google-auth-oauthlib` (YouTube auth)
- `requests` (HTTP requests)
- `asyncio` (async task processing)

### Task Storage
- **Phase 1**: In-memory storage for simplicity
- Tasks lost on application restart
- Suitable for personal use cases with immediate processing

### Error Handling
- Fail-fast approach: stop all related tasks on first failure
- Preserve original API error messages
- No automatic retry logic (Phase 1)

## Platform Support

### Phase 1 (MVP)
- **YouTube**: Video upload with metadata
- **Facebook**: Post publishing with links
- **Vimeo**: Video upload alternative

### Future Considerations
- Twitter/X integration
- LinkedIn publishing
- Instagram support
- Google Drive storage
- Batch processing capabilities

## Security Considerations

### Credential Management
- JSON file-based credential storage
- Credentials stored outside of project directory
- No credential logging or console output
- Secure token refresh handling

### API Compliance
- Respect platform rate limits
- Follow platform-specific terms of service
- Implement proper OAuth flows
- Handle token expiration gracefully

## Development Phases

### Phase 1: MVP
- Core MedusaCore interface
- YouTube + Facebook integration
- Basic task tracking (in-memory)
- JSON configuration
- Simple error handling

### Phase 2: Enhancement
- Additional platforms (Twitter, LinkedIn)
- Persistent task storage
- Retry mechanisms
- Enhanced error reporting

### Phase 3: Advanced Features
- Bulk upload capabilities
- Scheduling functionality
- Webhook notifications
- Performance optimization

## Usage Examples

### Basic Video Upload and Social Sharing
```python
# Upload video to YouTube and share on Facebook
task_id = medusa.publish_async(
    media_file="vacation_video.mp4",
    platforms=["youtube", "facebook"],
    metadata={
        "youtube": {
            "title": "Amazing Vacation 2024",
            "description": "Our trip to the mountains",
            "privacy": "public"
        },
        "facebook": {
            "message": "Just uploaded our vacation video! {youtube_url} #vacation2024"
        }
    }
)
```

### Multi-platform Publishing
```python
# Publish to multiple platforms simultaneously
task_id = medusa.publish_async(
    media_file="presentation.mp4",
    platforms=["youtube", "vimeo", "facebook"],
    metadata={
        "youtube": {"title": "Tech Talk 2024", "privacy": "unlisted"},
        "vimeo": {"title": "Tech Talk 2024", "privacy": "private"},
        "facebook": {"message": "My latest tech presentation: {youtube_url}"}
    }
)
```

### Status Monitoring
```python
import time

while True:
    status = medusa.get_task_status(task_id)
    print(f"Status: {status['status']}")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(10)  # Check every 10 seconds
```

## Risk Assessment

### Technical Risks
- **API Changes**: Platform APIs may change, breaking integrations
- **Rate Limiting**: Exceeding API limits could block operations
- **Authentication**: Token expiration could interrupt uploads
- **File Size Limits**: Large files may exceed platform limits

### Mitigation Strategies
- Regular API compatibility testing
- Implement rate limiting awareness
- Automatic token refresh mechanisms
- Pre-upload file validation

### Security Risks
- **Credential Exposure**: Config files contain sensitive tokens
- **Data Privacy**: Media files may contain sensitive content
- **Platform Compliance**: Automated posting may violate terms of service

### Mitigation Strategies
- Secure credential storage recommendations
- User education on data handling
- Clear documentation of platform compliance requirements