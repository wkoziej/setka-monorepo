# ABOUTME: CLI tool for managing Raspberry Pi cameras via SSH
# ABOUTME: Handles camera streaming setup, systemd service deployment, and monitoring

import argparse
import ipaddress
import subprocess
import sys


def validate_ip(addr: str) -> bool:
    """Return True iff ``addr`` is a syntactically valid IP address.

    Both camera_ip and obs_host are interpolated into ssh targets and the
    systemd unit. Validating them as real IPs blocks injection of shell
    metacharacters via a hostile "host" argument.
    """
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False


def deploy_to_camera(camera_ip: str, port: int = 5000, obs_host: str = "192.168.8.179"):
    """Deploy camera streaming setup to Raspberry Pi via SSH"""

    if not validate_ip(camera_ip):
        print(f"Error: invalid camera IP address: {camera_ip}", file=sys.stderr)
        return False
    if not validate_ip(obs_host):
        print(f"Error: invalid OBS host IP address: {obs_host}", file=sys.stderr)
        return False

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

    unit_path = f"/etc/systemd/system/camera-stream-{port}.service"

    # Write the unit file by piping its content over stdin to `sudo tee`,
    # rather than `echo '<content>' | sudo tee ...`. The old form interpolated
    # the whole unit into a shell command string, so any quote in the content
    # could break out of the single quotes.
    write_unit = subprocess.run(
        ["ssh", f"pi@{camera_ip}", "sudo", "tee", unit_path],
        input=service_content,
        capture_output=True,
        text=True,
    )
    if write_unit.returncode != 0:
        print(f"Error on {camera_ip}: {write_unit.stderr}")
        return False
    print(f"✓ {camera_ip}: wrote {unit_path}")

    # Remaining management commands operate only on the (numeric) port.
    commands = [
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
    if not validate_ip(camera_ip):
        print(f"Error: invalid camera IP address: {camera_ip}", file=sys.stderr)
        return False

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

    # All subcommands interpolate camera_ip into an ssh target — validate once,
    # up front, so restart/stop are guarded too (deploy/status also re-check).
    if not validate_ip(args.camera_ip):
        print(f"Error: invalid camera IP address: {args.camera_ip}", file=sys.stderr)
        sys.exit(1)

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
