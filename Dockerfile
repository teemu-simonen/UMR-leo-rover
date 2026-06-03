# 1. Start with the official ROS 2 Jazzy desktop image
FROM osrf/ros:jazzy-desktop

# 2. Install basic Linux utilities, ROS dependencies, and tbb
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    git \
    nano \
    wget \
    unzip \
    ros-jazzy-pcl-ros \
    ros-jazzy-pcl-conversions \
    libgflags-dev \
    libgoogle-glog-dev \
    libtbb-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Python packages required by data_exporter and laz_converter
RUN pip3 install --break-system-packages --ignore-installed open3d laspy pyproj numpy pyyaml "setuptools<80"

# 4. Download and Compile GTSAM (Dependency for sam-qn)
RUN wget -O gtsam.zip https://github.com/borglab/gtsam/archive/refs/tags/4.1.1.zip && \
    unzip gtsam.zip -d /tmp/ && \
    cd /tmp/gtsam-4.1.1 && \
    mkdir build && cd build && \
    cmake -DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF -DGTSAM_USE_SYSTEM_EIGEN=ON .. && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/gtsam-4.1.1 gtsam.zip

# 5. Download and Compile TEASER++ (Dependency for quatro)
RUN git clone https://github.com/MIT-SPARK/TEASER-plusplus.git /tmp/teaser && \
    cd /tmp/teaser && \
    mkdir build && cd build && \
    cmake -DENABLE_DIAGNOSTIC_PRINT=OFF -DBUILD_TEASER_FPFH=ON .. && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/teaser

# 6. Set up the internal ROS 2 workspace
WORKDIR /home/ros2_ws

# 7. Copy your local ROS 2 source code into the image
COPY ros2_dev/src /home/ros2_ws/src

# 8. Compile the full C++ and Python workspace internally
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && colcon build"

# 9. Automatically source ROS 2 environments every time the container starts
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
RUN echo "source /home/ros2_ws/install/setup.bash" >> ~/.bashrc

CMD ["/bin/bash"]