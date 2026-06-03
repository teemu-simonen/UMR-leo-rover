# Leo Rover SLAM & Georeferencing Pipeline

A fully containerized, automated pipeline for processing LiDAR data, performing SLAM, and exporting georeferenced point clouds.

This project wraps complex C++ robotics algorithms, MIT mathematical libraries (TEASER++), and TUM's FlexCloud into a single, Docker environment. You do not need to install ROS 2 or any C++ dependencies to run this.

## 🚀 Features
* **Phase 1 (SLAM):** Plays rosbags, processes LiDAR via SAM-QN, and tracks odometry.
* **Phase 2 (FlexCloud):** Automatically rubber-sheets the local SLAM map to global GPS coordinates using keyframe interpolation.
* **Phase 3 (Export):** Converts the final 3D map into a standard, uncompressed `.las` file for GIS LumiDB.

## 📋 Prerequisites
You only need two things installed on your host machine:
1. [Git](https://git-scm.com/)
2. [Docker](https://docs.docker.com/engine/install/)

## 🛠️ Installation

**1. Clone this repository to your dev pc:**
```bash
git clone https://github.com/teemu-simonen/UMR-leo-rover.git
cd leo_rover_slam
```

## Usage

### 1. Record a Lidar-rosbag using Leo-Rover:**
**SSH into Leo-Rover Jetson Orin Nano:**
```bash
ssh iot@192.168.1.200
```

**Start recording Lidar-data and save it into a rosbag:**

```bash
ros2 launch unitree_lidar_ros2 launch.py record:=true rosbag_name:=your rosbag name
```
- ros2 launch unitree_lidar_ros2 launch.py - launch the Lidar
- record:=true - Specify if you want to record a rosbag, set to false if no rosbag
- rosbag_name:=<our rosbag name - specify rosbag name

### 2. Copy the rosbag and run mapping pipeline
**Run the following commands from dev pc**
**Copy the rosbag**
```bash
scp -r iot@192.168.1.200:~/<filepath to rosbag>
```
