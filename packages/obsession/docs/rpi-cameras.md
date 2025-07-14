
## Raspberry Pi Camera Integration with OBS Studio

### Overview
This section documents the setup for streaming Raspberry Pi cameras to OBS Studio using GStreamer and the obs-gstreamer plugin.

### Prerequisites
- Raspberry Pi with libcamera-enabled camera (CSI or USB)
- OBS Studio with obs-gstreamer plugin installed
- Network connectivity between Raspberry Pi and OBS Studio machine
- GStreamer 1.22+ on Raspberry Pi

### Part 1: Raspberry Pi Camera Stream Setup

#### 1.1 Camera Stream Command
On Raspberry Pi, use this command to stream camera over UDP:

```bash
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=1000 ! queue ! rtph264pay ! queue ! udpsink host=192.168.8.179 port=5000
```

#### 1.2 Multi-Camera Setup
For multiple cameras, use different ports:

**Camera 1 (port 5000):**
```bash
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=1000 ! queue ! rtph264pay ! queue ! udpsink host=192.168.8.179 port=5000
```

**Camera 2 (port 5001):**
```bash
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=1000 ! queue ! rtph264pay ! queue ! udpsink host=192.168.8.179 port=5001
```

#### 1.3 Stream Parameters Explanation
- `libcamerasrc`: Modern camera source for Raspberry Pi
- `video/x-raw,width=640,height=480,framerate=30/1`: Output format specification
- `videoconvert`: Format conversion if needed
- `queue`: Buffering elements for smooth streaming
- `x264enc tune=zerolatency bitrate=1000`: H.264 encoding optimized for low latency
- `rtph264pay`: RTP payload for H.264 stream
- `udpsink host=192.168.8.179 port=5000`: UDP destination (replace with OBS machine IP)

### Part 2: OBS Studio Configuration

#### 2.1 obs-gstreamer Plugin Installation
The obs-gstreamer plugin must be compiled and installed:

```bash
# Install dependencies
sudo apt install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev meson

# Clone and compile
cd /home/user/dev
git clone https://github.com/fzwoch/obs-gstreamer.git
cd obs-gstreamer
PKG_CONFIG_PATH=/path/to/obs-studio/build/libobs meson setup build --buildtype=release
ninja -C build
ninja -C build install
```

#### 2.2 OBS Studio Source Configuration

1. **Add GStreamer Source:**
   - In OBS Studio: Sources → Add → GStreamer Source
   - Name the source (e.g., "Raspberry Pi Camera 1")

2. **Pipeline Configuration:**
   ```
   udpsrc port=5000 ! application/x-rtp,encoding-name=H264,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! video.
   ```

3. **Settings Configuration:**
   - ✅ Use pipeline time stamps (video)
   - ✅ Use pipeline time stamps (audio)
   - ✅ Sync appsink to clock (video)
   - ✅ Sync appsink to clock (audio)
   - ❌ Disable asynchronous state change in appsink (video)
   - ❌ Disable asynchronous state change in appsink (audio)
   - ✅ Try to restart when end of stream is reached
   - ❌ Try to restart after pipeline encountered an error
   - Error timeout (ms): `2000`
   - ✅ Stop pipeline when hidden
   - ✅ Clear image data after end-of-stream or error

#### 2.3 Multi-Camera Configuration
For multiple cameras, create separate GStreamer sources with different ports:

**Camera 1 Pipeline:**
```
udpsrc port=5000 ! application/x-rtp,encoding-name=H264,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! video.
```

**Camera 2 Pipeline:**
```
udpsrc port=5001 ! application/x-rtp,encoding-name=H264,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! video.
```

### Part 3: Troubleshooting

#### 3.1 Common Issues

**Camera not detected:**
- Check `libcamera-hello --list-cameras`
- Ensure camera is enabled in `/boot/firmware/config.txt`

**Stream fails to start:**
- Verify network connectivity: `ping 192.168.8.179`
- Check firewall settings on OBS machine
- Ensure no other process is using the camera

**OBS shows no video:**
- Verify stream is running on Raspberry Pi
- Check pipeline syntax in OBS
- Test with GStreamer on OBS machine: `gst-launch-1.0 udpsrc port=5000 ! application/x-rtp,encoding-name=H264,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink`

#### 3.2 Performance Optimization

**For better performance:**
- Increase bitrate: `bitrate=2000` (adjust based on network)
- Use hardware encoding if available: `v4l2h264enc` instead of `x264enc`
- Adjust resolution: `width=1280,height=720` for higher quality

**For lower latency:**
- Reduce bitrate: `bitrate=500`
- Lower resolution: `width=320,height=240`
- Add buffer size control: `udpsink host=192.168.8.179 port=5000 buffer-size=65536`

### Part 4: Network Configuration

#### 4.1 IP Address Configuration
Replace `192.168.8.179` with your OBS Studio machine IP address:
```bash
# Find OBS machine IP
ip addr show
```

#### 4.2 Port Management
- Default ports: 5000, 5001, 5002...
- Ensure ports are not blocked by firewall
- Use different ports for each camera stream

### Part 5: Automation Scripts

#### 5.1 Raspberry Pi Startup Script
Create `/home/pi/start_camera.sh`:
```bash
#!/bin/bash
# Camera streaming startup script
OBS_HOST="192.168.8.179"
CAMERA_PORT="5000"
RESOLUTION="640x480"
FRAMERATE="30"
BITRATE="1000"

gst-launch-1.0 libcamerasrc ! \
  video/x-raw,width=${RESOLUTION%x*},height=${RESOLUTION#*x},framerate=${FRAMERATE}/1 ! \
  videoconvert ! queue ! \
  x264enc tune=zerolatency bitrate=${BITRATE} ! \
  queue ! rtph264pay ! queue ! \
  udpsink host=${OBS_HOST} port=${CAMERA_PORT}
```

Make executable: `chmod +x /home/pi/start_camera.sh`

#### 5.2 Multi-Camera Script
Create `/home/pi/start_all_cameras.sh`:
```bash
#!/bin/bash
# Start multiple camera streams
OBS_HOST="192.168.8.179"

# Camera 1
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=1000 ! queue ! rtph264pay ! queue ! udpsink host=${OBS_HOST} port=5000 &

# Camera 2  
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=1000 ! queue ! rtph264pay ! queue ! udpsink host=${OBS_HOST} port=5001 &

echo "All cameras started"
```

This configuration provides low-latency, synchronized video streaming from Raspberry Pi cameras to OBS Studio with full control over encoding parameters and network settings.