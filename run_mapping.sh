#!/bin/bash

# Automatically detect where this script is saved on the host machine
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$1" ]; then
  echo "ERROR: You must provide the path to the rosbag."
  echo "Usage: ./run_mapping.sh rosbags/haaga_skannaus_1"
  exit 1
fi

BAG_PATH=$1
BAG_NAME=$(basename "$BAG_PATH") # <-- ADD THIS LINE BACK

# Open screen permissions safely for ALL local Docker containers (Rviz2 & FlexCloud)
xhost +local:root > /dev/null

echo "=========================================="
echo "      PHASE 1: ROS 2 SLAM PIPELINE        "
echo "=========================================="

# Run Phase 1 using Docker Compose (automatically handles volume mounts!)
# We use the -f flag to ensure it finds the compose file no matter where you run the script from
docker compose -f "$REPO_DIR/docker-compose.yml" run --rm slam bash -c " \
    source /opt/ros/jazzy/setup.bash && \
    source /home/ros2_ws/install/setup.bash && \
    ros2 launch leo_rover_mapping leo_mapping.py bag:=/home/ros2_ws/rosbags/$BAG_NAME && \
    mv /home/ros2_ws/install/sam-qn/share/sam-qn/result.pcd /home/ros2_ws/outputs/sam-qn_finished.pcd \
"

echo "=========================================="
echo "      PHASE 2: FLEXCLOUD GEOREFERENCING   "
echo "=========================================="

# Run FlexCloud (Since FlexCloud isn't in our compose file, we keep the dynamic docker run)
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
        ./build/georeferencing /datasets/FlexCloud/config/georeferencing.yaml /datasets/outputs/positions_interpolated.txt /datasets/outputs/poses_keyframes.txt /datasets/outputs/sam-qn_finished.pcd \
    "

echo "=========================================="
echo "      PHASE 3: CONVERTING TO LAS          "
echo "=========================================="

# Run Phase 3 using Docker Compose
docker compose -f "$REPO_DIR/docker-compose.yml" run --rm slam bash -c " \
    python3 /home/ros2_ws/scripts/laz_converter.py \
"

# Revoke GUI permissions to secure your host machine
xhost -local:root > /dev/null

echo "=========================================="
echo "          PIPELINE FINISHED!              "
echo "=========================================="