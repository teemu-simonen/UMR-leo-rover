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

**1. Clone this repository:**
```bash
git clone [https://github.com/YOUR_USERNAME/leo_rover_slam.git](https://github.com/YOUR_USERNAME/leo_rover_slam.git)
cd leo_rover_slam