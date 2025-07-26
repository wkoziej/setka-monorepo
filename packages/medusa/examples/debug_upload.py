#!/usr/bin/env python3
"""
Debug YouTube upload issue
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, "src")

from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig


async def debug_upload():
    """Debug YouTube upload step by step."""

    print("🔍 YouTube Upload Debug")
    print("=" * 30)

    # Setup
    config = PlatformConfig(
        platform_name="youtube",
        credentials={
            "client_secrets_file": "client_secrets.json",
            "credentials_file": "credentials.json",
        },
    )

    uploader = YouTubeUploader(config=config)

    try:
        # Step 1: Auth
        print("🔐 Step 1: Authentication...")
        await uploader.authenticate()
        print("✅ Authentication OK")

        # Step 2: Direct API test
        print("\n🧪 Step 2: Direct API test...")
        from googleapiclient.discovery import build

        service = build("youtube", "v3", credentials=uploader.auth_manager.credentials)

        # Test simple call
        print("Testing channels.list...")
        channels = service.channels().list(part="id", mine=True).execute()
        print(f"Channels response: {channels}")

        # Step 3: Try minimal upload request
        print("\n📤 Step 3: Minimal upload test...")

        # Create minimal metadata
        metadata = MediaMetadata(
            title="Debug Test",
            description="Debug test upload",
            privacy="private",
            tags=["debug", "test"],
        )

        # Convert to YouTube format
        youtube_metadata = uploader._convert_metadata_to_youtube_format(metadata)
        print(f"YouTube metadata: {youtube_metadata}")

        # Test file
        if not os.path.exists("test_video.mp4"):
            print("❌ test_video.mp4 not found")
            return

        print(f"File size: {os.path.getsize('test_video.mp4')} bytes")

        # Try to create upload request
        print("\n🎬 Step 4: Creating upload request...")

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(
                "test_video.mp4", chunksize=-1, resumable=True, mimetype="video/mp4"
            )

            insert_request = service.videos().insert(
                part=",".join(youtube_metadata.keys()),
                body=youtube_metadata,
                media_body=media,
            )

            print("✅ Upload request created successfully")

            # Try to execute (this is where it might fail)
            print("\n🚀 Step 5: Executing upload...")

            response = None
            status = None

            # First chunk
            try:
                status, response = insert_request.next_chunk()
                print(f"First chunk status: {status}")
                print(f"First chunk response: {response}")

                if response:
                    print("🎉 Upload started successfully!")
                    print(f"Video ID: {response.get('id', 'Unknown')}")

                    # Cancel upload (since it's just a test)
                    print("⏹️  Canceling test upload...")

                else:
                    print("🔄 Upload in progress...")

            except Exception as upload_error:
                print(f"❌ Upload execution failed: {upload_error}")
                print(f"Error type: {type(upload_error)}")

                # Check specific error details
                if hasattr(upload_error, "resp"):
                    print(f"HTTP status: {upload_error.resp.status}")
                    print(f"HTTP reason: {upload_error.resp.reason}")

                if hasattr(upload_error, "content"):
                    print(f"Error content: {upload_error.content}")

                # Check if it's the signup error
                error_str = str(upload_error)
                if "youtubeSignupRequired" in error_str:
                    print("\n💡 Diagnosis: YouTube channel not properly set up")
                    print("Solutions:")
                    print("1. Go to https://studio.youtube.com/")
                    print("2. Complete channel setup")
                    print("3. Verify phone number if required")
                    print("4. Accept YouTube Partner Program terms")
                elif "quotaExceeded" in error_str:
                    print("\n💡 Diagnosis: API quota exceeded")
                elif "forbidden" in error_str.lower():
                    print("\n💡 Diagnosis: Insufficient permissions")
                else:
                    print(f"\n💡 Diagnosis: Unknown error - {error_str}")

        except Exception as request_error:
            print(f"❌ Failed to create upload request: {request_error}")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_upload())
