# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Medusa is a Python library for automating media uploads to hosting platforms (YouTube, Vimeo) and subsequent social media publishing (Facebook, Twitter). The architecture follows a two-step process: first upload media to a hosting platform, then publish links to social media platforms.

## Development Commands

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file or test
uv run pytest tests/test_models.py
uv run pytest -k "test_task_result_creation"

# Run with coverage
uv run pytest --cov=src/medusa

# Run only unit tests (skip integration)
uv run pytest -m "not integration"

# Run integration tests only
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add package_name

# Create virtual environment
uv venv
```

## Architecture Overview

### Core Components

1. **Uploaders** (`src/medusa/uploaders/`)
   - Base class: `BaseUploader` - defines interface for all uploaders
   - Implementations: `YouTubeUploader`, `MockUploader`
   - Handle media upload to hosting platforms
   - Return URLs for social media publishing

2. **Publishers** (`src/medusa/publishers/`)
   - Base class: `BasePublisher` - defines interface for all publishers
   - Implementations: `FacebookPublisher`, `MockPublisher`
   - Post content with media URLs to social platforms
   - Support scheduling and immediate posting

3. **Task Management** (`src/medusa/utils/task_manager.py`)
   - In-memory task tracking with state transitions
   - Status: PENDING → RUNNING → COMPLETED/FAILED
   - Fail-fast architecture: stop all if primary fails

4. **Configuration** (`src/medusa/utils/config.py`)
   - JSON-based configuration with environment variable overrides
   - Pattern: `MEDUSA_{PLATFORM}_{FIELD}`
   - Validates platform configurations before use

5. **Models** (`src/medusa/models.py`)
   - `MediaMetadata`: Media information container
   - `PlatformConfig`: Platform-specific settings
   - `PublishRequest`: Orchestration request model
   - `TaskResult`: Async operation tracking

### Testing Architecture

- **Test Organization**: Mirrors source structure in `tests/`
- **Fixtures**: Centralized in `conftest.py` with factories for test data
- **Test Data**: JSON fixtures in `tests/fixtures/`
- **Coverage**: Minimum 95% required
- **Markers**: `unit`, `integration`, `slow`, `async_test`, `mock_api`, `manual`

### Platform Integration Patterns

Each platform integration follows this pattern:
1. Configuration validation in platform class
2. Authentication (OAuth for YouTube, tokens for others)
3. Media processing if needed (thumbnails, format conversion)
4. API interaction with comprehensive error handling
5. Result validation and status reporting

### Error Handling

Custom exception hierarchy in `src/medusa/exceptions.py`:
- `MedusaError`: Base exception
- Platform-specific: `YouTubeError`, `FacebookError`, etc.
- Operation-specific: `ConfigurationError`, `ValidationError`, `UploadError`

### Async Architecture

- All uploaders and publishers are async
- Use `asyncio` for concurrent operations
- Task manager coordinates async tasks
- Proper cleanup on failures

## Platform-Specific Notes

### YouTube
- Uses OAuth2 authentication flow
- Requires `client_secrets.json` and credentials storage
- Setup script: `scripts/setup_youtube_api.sh`
- Supports resumable uploads for large files

### Facebook
- Uses page access tokens
- Supports scheduled posts
- Requires page_id configuration
- Currently implementing scheduled post functionality

## Development Guidelines

1. **Always use TDD**: Write tests before implementation
2. **No mock mode in production**: Only real API interactions
3. **Validate early**: Check configurations before API calls
4. **Handle errors specifically**: Use custom exceptions
5. **Maintain test coverage**: Keep above 95%
6. **Follow async patterns**: All platform operations should be async

## Current Development Status

The project is ~65% complete. Core infrastructure is done, YouTube integration works, Facebook basic posting works. Currently implementing:
- Facebook scheduled posts
- Core orchestration module (MedusaCore)
- Additional platforms (Vimeo, Twitter)

## Credential Management

- Store credentials in JSON files (not in repo)
- Use environment variables for CI/CD
- YouTube: OAuth flow with stored credentials
- Facebook: Page access tokens
- All credential files must be in `.gitignore`
