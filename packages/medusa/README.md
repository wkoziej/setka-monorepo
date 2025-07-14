# Medusa - Media Upload & Social Automation

<div align="center">
  <img src="images/medusa.png" alt="Medusa Logo" width="300">
</div>

A Python library for automating media uploads to hosting platforms (YouTube, Vimeo) and subsequent social media publishing (Facebook, Twitter). Designed for personal publishing workflows with asynchronous task processing and status tracking.

## Features

- 🚀 **Asynchronous Processing**: Non-blocking uploads with task tracking
- 🔗 **Cross-Platform Dependencies**: Upload to YouTube → Auto-post to Facebook with link
- 📊 **Status Monitoring**: Real-time task status with detailed error reporting
- 🛡️ **Fail-Fast Architecture**: Stop all tasks if primary platform fails
- ⚙️ **JSON Configuration**: Simple credential and settings management

## Quick Start

### Installation

```bash
pip install medusa
```

### Basic Usage

```python
from medusa import MedusaCore

# Initialize with config file
medusa = MedusaCore(config_file="medusa_config.json")

# Upload and publish asynchronously
task_id = medusa.publish_async(
    media_file="my_video.mp4",
    platforms=["youtube", "facebook"],
    metadata={
        "youtube": {
            "title": "My Amazing Video",
            "description": "Check out this video!",
            "privacy": "public"
        },
        "facebook": {
            "message": "Just uploaded a new video! {youtube_url}"
        }
    }
)

# Check status
status = medusa.get_task_status(task_id)
print(f"Status: {status['status']}")
```

### Configuration

Create `medusa_config.json`:

```json
{
    "youtube": {
        "client_secrets_file": "secrets/youtube_client_secrets.json",
        "credentials_file": "secrets/youtube_credentials.json"
    },
    "facebook": {
        "page_id": "your_page_id",
        "access_token": "your_access_token"
    }
}
```

## Supported Platforms

### Upload Platforms
- ✅ YouTube (video upload with metadata)
- 🔄 Vimeo (planned)
- 🔄 Google Drive (planned)

### Social Platforms  
- ✅ Facebook (post publishing with links)
- 🔄 Twitter/X (planned)
- 🔄 LinkedIn (planned)

## Documentation

- [Getting Started Guide](docs/getting_started.md)
- [API Reference](docs/api_reference.md)
- [Configuration Guide](examples/config_example.json)
- [Web App Integration](examples/web_app_integration.py)

## Development

### Setup

```bash
git clone https://github.com/wojtas/medusa.git
cd medusa
uv sync
```

### Testing

```bash
uv run pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

This is a personal project, but feel free to open issues or submit pull requests for improvements.