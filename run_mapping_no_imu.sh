#!/bin/bash

# Ensure a rosbag was provided
if [ -z "$1" ]; then
    echo "Error: Please provide the path to your rosbag."
    echo "Usage: ./run_pipeline.sh rosbags/haaga_skannaus_1"
    exit 1
fi

BAG_PATH=$1
OUTPUT_DIR="$HOME/leo_rover_slam/outputs"

# SOURCE YOUR KISS-ICP WORKSPACE
source /opt/ros/jazzy/setup.bash
source "$HOME/kiss_test/install/setup.bash"

echo "========================================"
echo " 🚀 STARTING LEO ROVER MAPPING PIPELINE"
echo "========================================"

# 1. Start the Data Exporter (Background)
echo "[1/4] Starting GPS Data Exporter..."
python3 scripts/data_exporter_no_imu.py &
EXPORTER_PID=$!

# 2. Start KISS-ICP Odometry (Background)
echo "[2/4] Starting KISS-ICP..."
ros2 launch kiss_icp odometry.launch.py topic:=/unilidar/cloud use_sim_time:=true > /dev/null 2>&1 &

# Wait 2 seconds to ensure TF tree is initialized
sleep 2

# 3. Start RTAB-Map Global Mapper (Background)
echo "[3/4] Starting RTAB-Map..."
ros2 launch rtabmap_launch rtabmap.launch.py \
    use_sim_time:=true \
    depth:=false \
    subscribe_scan_cloud:=true \
    scan_cloud_topic:=/unilidar/cloud \
    visual_odometry:=false \
    odom_topic:=/kiss/odometry \
    frame_id:=unilidar_lidar \
    approx_sync:=true \
    args:="-d --Reg/Strategy 1 --Icp/VoxelSize 0.2 --Icp/PointToPlane true --RGBD/CreateOccupancyGrid false" > /dev/null 2>&1 &

# 4. Play the Rosbag (Foreground - the script will wait here until the bag ends)
echo "[4/4] Playing Rosbag (skipping first 5 seconds of boot noise)..."
ros2 bag play "$BAG_PATH" --clock --start-offset 5.0

echo "========================================"
echo " 🛑 BAG FINISHED. FLUSHING DATABASES..."
echo "========================================"

# Gracefully kill the background nodes so they save their data safely
# (Using pkill to target the true C++ engines instead of the Python wrappers)
pkill -INT -f rtabmap
pkill -INT -f kiss_icp_node
kill -INT $EXPORTER_PID 2>/dev/null

echo "Waiting for RTAB-Map to optimize and save the database (this takes 10-30 seconds)..."

# Wait until the actual RTAB-Map engine has completely disappeared
while pgrep -f rtabmap > /dev/null; do
    sleep 1
done

echo "========================================"
echo " 💾 EXPORTING GLOBAL POINT CLOUD"
echo "========================================"
# Note: Added the required --cloud flag
rtabmap-export --cloud --scan --output_dir "$OUTPUT_DIR" ~/.ros/rtabmap.db

echo "========================================"
echo " 🧹 RUNNING AUTOMATED CLEANUP"
echo "========================================"

# Trim the Odometry Overhang
echo "Trimming the last 4 seconds of odometry to fix FlexCloud brackets..."
head -n -40 "$OUTPUT_DIR/odometry.txt" > "$OUTPUT_DIR/odom_trimmed.txt"
mv -f "$OUTPUT_DIR/odom_trimmed.txt" "$OUTPUT_DIR/odometry.txt"

# Sanitize and Convert the PLY to PCD
echo "Converting PLY to PCD to fix scalar field errors..."
python3 -c "
import open3d as o3d
import os

ply_file = '$OUTPUT_DIR/rtabmap_cloud.ply'
if not os.path.exists(ply_file):
    ply_file = '$OUTPUT_DIR/cloud_0.ply' 

pcd_file = '$OUTPUT_DIR/rtabmap_cloud.pcd'

if os.path.exists(ply_file):
    pcd = o3d.io.read_point_cloud(ply_file)
    o3d.io.write_point_cloud(pcd_file, pcd)
    print('Success! Created rtabmap_cloud.pcd')
else:
    print('Warning: Could not find PLY file to convert in $OUTPUT_DIR')
"

echo "✅ Pipeline Complete! Your PCD and text files are perfectly formatted and waiting in: $OUTPUT_DIR"