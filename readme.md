# Leo Rover Mapping

## Introduction
This repository contains a high-performance 3D mapping pipeline for the Leo Rover. It is designed to support two hardware configurations:

This project is fully containerized using Docker to ensure consistent compilation across different computers. It automates the entire flow from raw ROS 2 bag files to georeferenced, terrain-aligned 3D point clouds.

---

## 1. Installation Instructions
This pipeline requires a Linux environment (Ubuntu 24.04 recommended). 

### Setup Dependencies
You will need
- Docker
- Git

### Clone the repository and build
```bash
git clone https://github.com/teemu-simonen/UMR-leo-rover.git
cd UMR-leo-rover

# Create the following directories
mkdir -p rosbags outputs

# Build the enviorement (may take about 10-20 minutes)
docker compose build

# Make the scripts executable
chmod +x run_mapping.sh run_mapping_no_imu.sh scripts/internal_mapping_no_imu.sh
```


## 2. Data Collection on Leo Rover
To ensure the pipeline generates accurate maps, please follow these collection guidelines:
- Try to drive the rover as smoothly as possible, avoid tight turns
- Enure that the rover antennas can see the sky to get gps data
- To get the georeferencing as accurate as possible, at the beginning of a scan, try to drive north about 10 meters

To start all sensors and begin recording a rosbag:
```bash
# Conncet to RUTX11 5G Network and SSH Into the Leo-Rover Jetson.
ssh <jetson-username>@<jetson-ip-address>
cd leo-rover/unilidar_sdk2/unitree_lidar_ros2/
source install/setup.bash

# Launch, by defeault a rosbag will be recorded, set record:=false if you don't want to record a rosbag
ros2 launch unitree_lidar_ros2 launch.py record:=true rosbag_name:=<your_rosbag_name>

# When done Ctrl+C to end and save the rosbag

```

## 4. Mapping and Georeferencing
Copy the recorded rosbags from leo-rover Jetson
```bash
# By default the rosbag will be saved on your pc in the rosbags folder in leo_rover_slam folder
scp -r <jetson_username>@<Jetson_IP_Address>:~/leo-rover/rosbags/<rosbag_name> ~/UMR-leo-rover/rosbags
```

There have been provided two ways to map the rosbag data, one if you have an imu avaivable and on without

### IMU Mapping
```bash
./run_mapping.sh rosbags/<YOUR_ROSBAG_NAME>
```

### No IMU Mapping
```bash
./run_mapping_no_imu.sh rosbags/<YOUR_ROSBAG_NAME>
```

Sometimes there may be permission errors on the finished pointclouds in the outputs folder. To fix them, use the following command
```bash
sudo chown -R $USER:$USER outputs/
```

# Stereocamera
To install stereocamera software, visit zedlab website and follow instructions:
 [ Getting Started with your ZED camera ](https://support.stereolabs.com/hc/en-us/articles/207616785-Getting-Started-with-your-ZE).

# Running stereocamera
Build docker image
```bash
docker build -f Dockerfile.camera -t ghcr.io/haitomatic/jaska-dev:camera .

# Run camera container:
Bash 

docker run -it --rm --name jaska_camera \ 
  --gpus all \ 
  --runtime=nvidia \ 
  --privileged \ 
  --network=host \ 
  --ipc=host \ 
  --pid=host \ 
  -v /dev:/dev \ 
  -v /tmp:/tmp \ 
  -v /tmp/argus_socket:/tmp/argus_socket \ 
  -v /var/nvidia/nvcam/settings/:/var/nvidia/nvcam/settings/ \ 
  -v /usr/local/zed/resources:/usr/local/zed/resources \ 
  -v /home/iot/haito_dev/zedx_recording:/Jaska/zedx_recording \ 
  --entrypoint /bin/bash \ 
  jaska-dev:camera-python

# Test the camera
python3 camera_test.py 

# Start recording
python3 record_svo2_zedx.py --output /Jaska/zedx_recording/<tallenteen nimi>.svo2 --compression H264 --no-preview 
```
Move the svo file to your dev pc with an nvidia gpu