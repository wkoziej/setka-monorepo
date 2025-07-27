#!/bin/bash
# ABOUTME: Batch deployment script for multiple Raspberry Pi cameras
# ABOUTME: Deploys systemd services to all cameras in the list

# List of camera IPs and ports
CAMERAS=(
    "192.168.8.158:5000"
    "192.168.8.160:5001"

)

OBS_HOST="192.168.8.179"

for camera in "${CAMERAS[@]}"; do
    IFS=':' read -ra ADDR <<< "$camera"
    IP="${ADDR[0]}"
    PORT="${ADDR[1]}"

    echo "Deploying to $IP:$PORT..."
    uv run python -m src.cli.cameras deploy "$IP" --port "$PORT" --obs-host "$OBS_HOST"

    if [ $? -eq 0 ]; then
        echo "✓ $IP:$PORT deployed successfully"
    else
        echo "✗ $IP:$PORT deployment failed"
    fi
done
