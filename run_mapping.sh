#!/bin/bash

# Automatically detect where this script is saved on the host machine
BASE_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ -z "$1" ]; then
  echo "ERROR: You must provide the path to the rosbag."
  echo "Usage: ./run_mapping.sh /path/to/your/bag"
  exit 1
fi

BAG_PATH=$1
BAG_NAME=$(basename "$BAG_PATH")

echo "=========================================="
echo "      PHASE 1: ROS 2 SLAM PIPELINE        "
echo "=========================================="

# Run your custom ROS 2 environment, mounting host directories inside
sudo docker run --rm \
    --network=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --privileged \
    -v "$BASE_DIR/rosbags:/home/ros2_ws/rosbags" \
    -v "$BASE_DIR/outputs:/home/ros2_ws/outputs" \
    leo_rover_pipeline:latest \
    /bin/bash -c " \
        source /opt/ros/jazzy/setup.bash && \
        source /home/ros2_ws/install/setup.bash && \
        ros2 launch leo_rover_mapping leo_mapping.py bag:=/home/ros2_ws/rosbags/$BAG_NAME && \
        mv /home/ros2_ws/install/sam-qn/share/sam-qn/result.pcd /home/ros2_ws/outputs/sam-qn_finished.pcd \
    "

echo "=========================================="
echo "      PHASE 2: FLEXCLOUD GEOREFERENCING   "
echo "=========================================="

# Open screen permissions for the FlexCloud Rerun Visualizer GUI
xhost +

sudo docker run --rm \
    --network=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --privileged \
    -v /dev/shm:/dev/shm \
    -v "$BASE_DIR/:/datasets/" \
    ghcr.io/tumftm/flexcloud:latest \
    /bin/bash -c " \
        echo '--> Running Keyframe Interpolation...' && \
        ./build/keyframe_interpolation /datasets/FlexCloud/config/keyframe_interpolation.yaml /datasets/outputs/gps_dir /datasets/outputs/odometry.txt /datasets/outputs/ && \
        echo '--> Running Georeferencing...' && \
        ./build/georeferencing /datasets/FlexCloud/config/georeferencing.yaml /datasets/outputs/positions_interpolated.txt /datasets/outputs/poses_keyframes.txt /datasets/outputs/sam-qn_finished.pcd \
    "

# Close GUI permissions
xhost -

echo "=========================================="
echo "      PHASE 3: CONVERTING TO LAS          "
echo "=========================================="

# Execute the converter script inside your image environment
sudo docker run --rm \
    -v "$BASE_DIR/outputs:/home/ros2_ws/outputs" \
    leo_rover_pipeline:latest \
    /bin/bash -c "python3 /home/ros2_ws/src/leo_rover_mapping/scripts/laz_converter.py"

echo "=========================================="
echo "          PIPELINE  FINISHED!             "
echo "=========================================="