#!/bin/bash

echo "Starting Environment Cleanup for Video Analytics Project..."

# 1. Kill any existing Uvicorn or FastAPI processes
echo "Stopping Python/Uvicorn processes..."
pkill -9 -f "uvicorn" || echo "No uvicorn processes found."
pkill -9 -f "main.py" || echo "No main.py processes found."

# 2. Kill zombie FFmpeg processes (from audio extraction)
echo "Cleaning up FFmpeg zombies..."
pkill -9 ffmpeg || echo "No ffmpeg processes found."

# 3. Clear Leaked Semaphores (IPC)
# This finds semaphores owned by the current user and removes them
echo "Clearing leaked IPC semaphores..."
IPCS_S=$(ipcs -s | awk -v user=$(whoami) '$3==user {print $2}')
if [ -z "$IPCS_S" ]; then
    echo "No leaked semaphores found."
else
    for id in $IPCS_S; do
        ipcrm -s $id
        echo "Removed semaphore ID: $id"
    done
fi

# 4. Clean up temporary files
echo "Cleaning temp/data directories..."
rm -rf ./temp/*
# Be careful with this line if you want to keep your uploaded videos
# rm -rf ./data/videos/* # 5. Reset Redis (if using Redis cache)
if command -v redis-cli &> /dev/null; then
    echo "Flushing Redis cache..."
    redis-cli FLUSHALL
fi

echo "Cleanup Complete. Your environment is fresh!"