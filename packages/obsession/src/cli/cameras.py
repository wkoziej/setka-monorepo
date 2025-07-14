# ABOUTME: CLI tool for managing Raspberry Pi cameras via SSH
# ABOUTME: Handles camera streaming setup, systemd service deployment, and monitoring

import argparse
import subprocess
import sys


def deploy_to_camera(camera_ip: str, port: int = 5000, obs_host: str = "192.168.8.179"):
    """Deploy camera streaming setup to Raspberry Pi via SSH"""

    # Create systemd service content
    service_content = f"""[Unit]
Description=Camera Stream on port {port}
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=1000 ! queue ! rtph264pay ! queue ! udpsink host={obs_host} port={port}
Restart=always
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
"""

    # Commands to run on RPI
    commands = [
        f"echo '{service_content}' | sudo tee /etc/systemd/system/camera-stream-{port}.service",
        "sudo systemctl daemon-reload",
        f"sudo systemctl enable camera-stream-{port}",
        f"sudo systemctl start camera-stream-{port}",
    ]

    for cmd in commands:
        result = subprocess.run(
            ["ssh", f"pi@{camera_ip}", cmd], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error on {camera_ip}: {result.stderr}")
            return False
        print(f"✓ {camera_ip}: {cmd}")

    return True


def check_camera_status(camera_ip: str, port: int = 5000):
    """Check if camera service is running"""
    result = subprocess.run(
        ["ssh", f"pi@{camera_ip}", f"sudo systemctl is-active camera-stream-{port}"],
        capture_output=True,
        text=True,
    )

    status = result.stdout.strip()
    print(f"Camera {camera_ip}:{port} - {status}")
    return status == "active"


def main():
    parser = argparse.ArgumentParser(description="Manage Raspberry Pi cameras")
    parser.add_argument("command", choices=["deploy", "status", "restart", "stop"])
    parser.add_argument("camera_ip", help="IP address of camera")
    parser.add_argument("--port", type=int, default=5000, help="Stream port")
    parser.add_argument("--obs-host", default="192.168.8.179", help="OBS machine IP")

    args = parser.parse_args()

    if args.command == "deploy":
        success = deploy_to_camera(args.camera_ip, args.port, args.obs_host)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        check_camera_status(args.camera_ip, args.port)

    elif args.command == "restart":
        subprocess.run(
            [
                "ssh",
                f"pi@{args.camera_ip}",
                f"sudo systemctl restart camera-stream-{args.port}",
            ]
        )

    elif args.command == "stop":
        subprocess.run(
            [
                "ssh",
                f"pi@{args.camera_ip}",
                f"sudo systemctl stop camera-stream-{args.port}",
            ]
        )


if __name__ == "__main__":
    main()
