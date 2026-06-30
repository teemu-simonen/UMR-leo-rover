#!/bin/bash

# Automatically detect where this script is saved on the host machine
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$1" ]; then
  echo "ERROR: You must provide the path to the rosbag."
  echo "Usage: ./run_mapping_no_imu.sh rosbags/haaga_skannaus_1"
  exit 1
fi

BAG_PATH=$1

# Open screen permissions safely for ALL local Docker containers
xhost +local:root > /dev/null

echo "=========================================="
echo "      PHASE 1: ROS 2 SLAM PIPELINE        "
echo "=========================================="

# Trigger the internal ROS 2 mapping script inside the container using Docker Compose
docker compose -f "$REPO_DIR/docker-compose.yml" run --rm slam bash -c " \
    /home/ros2_ws/scripts/internal_mapping_no_imu.sh $BAG_PATH \
"

echo "=========================================="
echo "      PHASE 2: FLEXCLOUD GEOREFERENCING   "
echo "=========================================="

sudo docker run --rm \
    --network=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --privileged \
    -v /dev/shm:/dev/shm \
    -v "$REPO_DIR/:/datasets/" \
    ghcr.io/tumftm/flexcloud:latest \
    /bin/bash -c " \
        echo '--> Running Keyframe Interpolation...' && \
        ./build/keyframe_interpolation /datasets/FlexCloud/config/keyframe_interpolation.yaml /datasets/outputs/gps_dir /datasets/outputs/odometry.txt /datasets/outputs/ && \
        echo '--> Running Georeferencing...' && \
        ./build/georeferencing /datasets/FlexCloud/config/georeferencing.yaml /datasets/outputs/positions_interpolated.txt /datasets/outputs/poses_keyframes.txt /datasets/outputs/rtabmap_cloud.pcd \
    "

echo "=========================================="
echo "      PHASE 3: CONVERTING TO LAS          "
echo "=========================================="

# Run the No-IMU Python converter inside the container
docker compose -f "$REPO_DIR/docker-compose.yml" run --rm slam bash -c " \
    python3 /home/ros2_ws/scripts/laz_converter_no_imu.py \
"

# Revoke GUI permissions to secure your host machine
xhost -local:root > /dev/null

echo "=========================================="
echo "          PIPELINE FINISHED!              "
echo "=========================================="