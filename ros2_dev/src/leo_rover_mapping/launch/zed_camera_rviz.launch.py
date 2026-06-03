#!/usr/bin/env python3

# Copyright 2025 Jaska Development Team
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Launch file to start RViz2 visualization with symlink fix for ZED mesh paths.
This creates a symlink to fix mesh path issues and cleans up on exit.
"""

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    LogInfo,
    ExecuteProcess
)
from launch.conditions import IfCondition
from launch.substitutions import (
    LaunchConfiguration,
    TextSubstitution
)
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    """Setup launch configuration based on parameters."""
    
    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Get parameter values
    use_sim_time_val = use_sim_time.perform(context).lower() == 'true'

    # Shared topic names
    zed_robot_description_topic = '/zed/robot_description'
    remapped_robot_description_topic = '/zed/robot_description_fixed'

    # RViz2 Configurations
    try:
        config_rviz2 = os.path.join(
            get_package_share_directory('jaska-dev'),
            'rviz',
            'zed_stereo.rviz'
        )
        if not os.path.exists(config_rviz2):
            # Fallback to workspace relative path
            config_rviz2 = os.path.join(
                os.path.expanduser('~/haito_dev/ros2_ws/src/jaska-dev/rviz'),
                'zed_stereo.rviz'
            )
    except Exception:
        # Fallback to workspace relative path
        config_rviz2 = os.path.join(
            os.path.expanduser('~/haito_dev/ros2_ws/src/jaska-dev/rviz'),
            'zed_stereo.rviz'
        )

    # Robot description path remapper node (Python content modifier)
    robot_description_remapper = ExecuteProcess(
        cmd=[
            'python3', '-c', f'''
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, HistoryPolicy, ReliabilityPolicy
from std_msgs.msg import String
import sys

class RobotDescriptionRemapper(Node):
    def __init__(self):
        super().__init__("robot_description_remapper")
        self.get_logger().info("Starting robot description remapper...")

        # QoS profile for robot description topics (transient local)
        robot_description_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # Subscribe to original robot description
        self.subscription = self.create_subscription(
            String,
            "{zed_robot_description_topic}",
            self.description_callback,
            robot_description_qos
        )
        
        # Publish fixed robot description
        self.publisher = self.create_publisher(
            String,
            "{remapped_robot_description_topic}",
            robot_description_qos
        )
        
        self.get_logger().info("Robot description remapper ready")

    def description_callback(self, msg):
        # Fix the mesh file paths
        fixed_data = msg.data.replace(
            "file:///root/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/",
            "package://zed_msgs/meshes/"
        )
        
        # Republish with fixed paths
        new_msg = String()
        new_msg.data = fixed_data
        self.publisher.publish(new_msg)
        
        self.get_logger().info("Published fixed robot description")

try:
    rclpy.init()
    node = RobotDescriptionRemapper()
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
finally:
    if rclpy.ok():
        rclpy.shutdown()
            '''
        ],
        output='screen',
        name='robot_description_remapper'
    )

    # RViz2 node with topic remapping
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', config_rviz2],
        parameters=[
            {
                'use_sim_time': use_sim_time_val
            }
        ],
        remappings=[
            (zed_robot_description_topic, remapped_robot_description_topic),
        ]
    )

    return [
        robot_description_remapper,
        rviz2_node,
    ]


def generate_launch_description():
    """Generate the launch description with all arguments."""
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time for RViz2 and remapper node.'),
        # Launch setup function
        OpaqueFunction(function=launch_setup)
    ])
