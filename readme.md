# 🚀 Leo Rover SLAM Architecture

## 1. Introduction
This repository contains a high-performance 3D mapping pipeline for the Leo Rover. It is designed to support two hardware configurations:
* **Point-LIO:** For rovers equipped with high-precision IMUs.
* **KISS-ICP:** A robust LiDAR-odometry approach for rovers without IMUs.

This project is fully containerized using Docker to ensure consistent compilation across different computers. It automates the entire flow from raw ROS 2 bag files to georeferenced, terrain-aligned 3D point clouds.

---

## 2. Installation Instructions
This pipeline requires a Linux environment (Ubuntu 24.04 recommended). 

### Setup Dependencies
On a fresh computer, install the necessary tools:
```bash
# Update and install Git
sudo apt update && sudo apt install git -y

# Install Docker
curl -fsSL [https://get.docker.com](https://get.docker.com) -o get-docker.sh
sudo sh get-docker.sh

# Add user to Docker group (allows running without sudo)
sudo usermod -aG docker $USER
newgrp docker

# Clone the repository
git clone https://github.com/teemu-simonen/UMR-leo-rover.git
cd leo_rover_slam

# This command installs all ROS 2 Jazzy dependencies and compiles the C++ SLAM nodes (Point-LIO, KISS-ICP, GTSAM, TEASER++).
docker build -t leo_rover_slam .
```
## 3. Data Collection on Leo Rover
To ensure the pipeline generates accurate maps, please follow these collection guidelines:
- Try to drive the rover as smoothly as possible, avoid tight turns
- Enure that the rover antennas can see the sky to get gps data
- To get the georeferencing as accurate as possible, at the beginning of a scan, try to drive north abou 10 meters

To start all sensors and begin recording a rosbag:
```bash
# SSH Into the Leo-Rover Jetson.
ssh <username>@<ip-address>
cd leo-rover/unilidar_sdk2/unitree_lidar_ros2/
source install/setup.bash

# Launch, by defeault a rosbag will be recorded, set record:=false if you don't want to record a rosbag
ros2 launch unitree_lidar_ros2 launch.py record:=true rosbag_name:=<your_rosbag_name>

# When done Ctrl+C to end and save the rosbag

#Copy the rosbag to your pc where you installed the SLAM-alghoritms, by default the rosbag will be saved on your pc in the rosbags folder in leo_rover_slam folder
scp -r <jetson_username>@<Jetson_IP_Address>:~/leo-rover/rosbags/<rosbag_name> ~/leo_rover_slam/rosbags
```

## 4. Mapping and Georeferencing
There have been provided two ways to map the rosbag data, one if you have an imu avaivable and on without

# IMU Mapping
```bash
./run_mapping.sh /home/username/leo_rover_dist/rosbags/<rosbag_name>
```
Enter the SLAM environment:
```bash
docker run -it --rm \
  --net=host \
  -v "$HOME/leo_rover_slam:/home/$USER/leo_rover_slam" \
  -w "/home/$USER/leo_rover_slam" \
  leo_rover_slam


```

