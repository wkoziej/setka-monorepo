#!/usr/bin/env python3
"""
Simple YouTube API test script.
Use this for quick manual testing without pytest complexity.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig


async def test_youtube_authentication():
    """Test YouTube authentication flow."""
    print("🔐 Testing YouTube Authentication...")
    
    # Check for credentials
    if not os.path.exists("client_secrets.json"):
        print("❌ Missing client_secrets.json file!")
        print("📋 Steps to get credentials:")
        print("   1. Go to Google Cloud Console")
        print("   2. Create project and enable YouTube Data API v3")
        print("   3. Create OAuth 2.0 credentials (Desktop App)")
        print("   4. Download as client_secrets.json")
        return False
    
    # Setup uploader
    config = PlatformConfig(
        platform_name="youtube",
        credentials={
            "client_secrets_file": "client_secrets.json",
            "credentials_file": "credentials.json"
        }
    )
    
    uploader = YouTubeUploader(config=config)
    
    try:
        print("🌐 Starting OAuth flow (browser will open)...")
        result = await uploader.authenticate()
        
        if result:
            print("✅ Authentication successful!")
            return uploader
        else:
            print("❌ Authentication failed!")
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


async def test_metadata_validation(uploader):
    """Test metadata validation."""
    print("\n📝 Testing metadata validation...")
    
    # Test valid metadata
    metadata = MediaMetadata(
        title="Test Video - Medusa Library",
        description="This is a test video for the Medusa automation library.",
        tags=["test", "medusa", "automation", "youtube", "api"],
        privacy="private",  # Always private for tests
        category="science"
    )
    
    try:
        uploader._validate_metadata(metadata)
        print("✅ Metadata validation passed!")
        
        # Test conversion
        youtube_format = uploader._convert_metadata_to_youtube_format(metadata)
        print(f"📊 Converted metadata: {youtube_format}")
        
        return metadata
        
    except Exception as e:
        print(f"❌ Metadata validation failed: {e}")
        return None


async def test_video_upload(uploader, metadata):
    """Test actual video upload."""
    print("\n📤 Testing video upload...")
    
    # Check for test video
    test_files = ["test_video.mp4", "test.mp4", "sample.mp4"]
    test_video = None
    
    for filename in test_files:
        if os.path.exists(filename):
            test_video = filename
            break
    
    if not test_video:
        print("⚠️  No test video found!")
        print(f"📁 Place one of these files in project root: {test_files}")
        print("💡 Tip: Use a small video file (< 50MB) for testing")
        return None
    
    print(f"📁 Using test video: {test_video}")
    file_size = os.path.getsize(test_video) / (1024 * 1024)  # MB
    print(f"📏 File size: {file_size:.1f} MB")
    
    # Add timestamp to title
    metadata.title = f"Medusa Test - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        print("🚀 Starting upload...")
        
        def progress_callback(progress):
            print(f"📈 Progress: {progress.percentage:.1f}% ({progress.bytes_uploaded}/{progress.total_bytes} bytes)")
        
        result = await uploader.upload_media(test_video, metadata, progress_callback)
        
        if result.success:
            print("✅ Upload successful!")
            print(f"📺 Video ID: {result.upload_id}")
            print(f"🔗 Video URL: {result.media_url}")
            print(f"🏷️  Title: {result.metadata.get('title', 'N/A')}")
            
            # Save result
            with open("upload_result.txt", "w") as f:
                f.write(f"Upload Result - {datetime.now()}\n")
                f.write(f"Video ID: {result.upload_id}\n")
                f.write(f"URL: {result.media_url}\n")
                f.write(f"Title: {result.metadata.get('title', 'N/A')}\n")
            
            print("💾 Result saved to upload_result.txt")
            print("🗑️  Remember to delete test video from YouTube Studio!")
            
            return result
        else:
            print(f"❌ Upload failed: {result.error}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None


async def main():
    """Main test function."""
    print("🎬 YouTube API Test Script")
    print("=" * 40)
    
    # Step 1: Authentication
    uploader = await test_youtube_authentication()
    if not uploader:
        return
    
    # Step 2: Metadata validation
    metadata = await test_metadata_validation(uploader)
    if not metadata:
        return
    
    # Step 3: Video upload (optional)
    print("\n" + "="*40)
    response = input("🤔 Do you want to test actual video upload? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        result = await test_video_upload(uploader, metadata)
        if result:
            print("\n🎉 All tests completed successfully!")
        else:
            print("\n❌ Upload test failed!")
    else:
        print("\n✅ Authentication and validation tests completed!")
    
    # Cleanup
    await uploader.cleanup()


if __name__ == "__main__":
    print("Starting YouTube API tests...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc() 