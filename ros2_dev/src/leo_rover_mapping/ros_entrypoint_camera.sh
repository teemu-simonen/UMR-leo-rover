#!/bin/bash
set -e

# setup ros2 environment
source "/opt/ros/$ROS_DISTRO/install/setup.bash"
source "/opt/ros/$ROS_DISTRO/setup.bash"
source "/root/ros2_ws/install/local_setup.bash"

# Welcome information
echo "ZED ROS2 Docker Image"
echo "---------------------"
echo 'ROS distro: ' $ROS_DISTRO
echo 'DDS middleware: ' $RMW_IMPLEMENTATION
echo 'ROS 2 Workspaces:' $COLCON_PREFIX_PATH
echo 'Local IPs:' $(hostname -I)
echo "---"  
echo 'Available ZED packages:'
ros2 pkg list | grep zed
echo "---------------------"
echo 'To start a ZED camera node:'
echo '  ros2 launch zed_wrapper zed_camera.launch.py camera_model:=<zed|zedm|zed2|zed2i|zedx|zedxm|zedxonegs|zedxone4k|zedxonehdr|virtual>'
echo "---------------------"
echo "For troubleshooting:"
echo "  /usr/local/zed/tools/ZED_Diagnostic"
echo "  /usr/local/zed/tools/ZED_Explorer"
exec "$@"
