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
Robot Description Path Remapper Node

This node subscribes to robot_description messages and republishes them
with corrected mesh file paths for RViz2 visualization. It fixes the issue
where ZED mesh files are not found due to incorrect paths in the URDF.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import re
import os


class RobotDescriptionRemapper(Node):
    """Node to remap robot description mesh paths for proper RViz2 display."""
    
    def __init__(self):
        super().__init__('robot_description_remapper')
        
        # Parameters
        self.declare_parameter('camera_name', 'zed')
        self.declare_parameter('use_sim_time', False)
        
        self.camera_name = self.get_parameter('camera_name').get_parameter_value().string_value
        use_sim_time = self.get_parameter('use_sim_time').get_parameter_value().bool_value
        
        # Set use_sim_time parameter
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=use_sim_time)])
        
        # Publisher and Subscriber
        self.subscription = self.create_subscription(
            String,
            'robot_description_in',
            self.robot_description_callback,
            10
        )
        
        self.publisher = self.create_publisher(
            String,
            'robot_description_out',
            10
        )
        
        # Mesh path mappings
        self.mesh_paths = self._setup_mesh_paths()
        
        self.get_logger().info(f'Robot Description Remapper started for camera: {self.camera_name}')
        self.get_logger().info(f'Mesh path mappings: {len(self.mesh_paths)} entries')
        
        # Log available mesh paths for debugging
        for original, corrected in self.mesh_paths.items():
            if os.path.exists(corrected):
                self.get_logger().debug(f'✓ {original} -> {corrected}')
            else:
                self.get_logger().warn(f'✗ {original} -> {corrected} (file not found)')
    
    def _setup_mesh_paths(self):
        """Setup mesh path mappings from problematic paths to correct ones."""
        mesh_mappings = {}
        
        # Common ZED mesh files that might have path issues
        zed_meshes = [
            'zed.stl', 'zedm.stl', 'zed2.stl', 'zed2i.stl', 
            'zedx.stl', 'zedxm.stl', 'zedxone.stl'
        ]
        
        # Possible problematic path patterns
        problematic_patterns = [
            '/root/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/',
            '/opt/ros/jazzy/install/zed_msgs/share/zed_msgs/meshes/',
            'package://zed_msgs/meshes/',
            'file:///root/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/',
        ]
        
        # Correct paths to try (in order of preference)
        correct_paths = [
            '/opt/ros/jazzy/share/zed_msgs/meshes/',
            '/root/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/',
            '/home/haito/haito_dev/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/',
        ]
        
        # Build mapping dictionary
        for mesh_file in zed_meshes:
            for problematic_pattern in problematic_patterns:
                problematic_path = problematic_pattern + mesh_file
                
                # Find the first existing correct path
                for correct_path_base in correct_paths:
                    correct_path = correct_path_base + mesh_file
                    if os.path.exists(correct_path):
                        mesh_mappings[problematic_path] = f'file://{correct_path}'
                        break
                else:
                    # Fallback to first correct path even if file doesn't exist
                    mesh_mappings[problematic_path] = f'file://{correct_paths[0]}{mesh_file}'
        
        return mesh_mappings
    
    def robot_description_callback(self, msg):
        """Process incoming robot description and fix mesh paths."""
        try:
            urdf_content = msg.data
            modified_urdf = self._fix_mesh_paths(urdf_content)
            
            # Publish the modified URDF
            modified_msg = String()
            modified_msg.data = modified_urdf
            self.publisher.publish(modified_msg)
            
            self.get_logger().debug('Robot description remapped and published')
            
        except Exception as e:
            self.get_logger().error(f'Error processing robot description: {str(e)}')
            # Publish original message as fallback
            self.publisher.publish(msg)
    
    def _fix_mesh_paths(self, urdf_content):
        """Fix mesh file paths in URDF content."""
        modified_urdf = urdf_content
        changes_made = 0
        
        # Apply all mesh path mappings
        for problematic_path, correct_path in self.mesh_paths.items():
            if problematic_path in modified_urdf:
                modified_urdf = modified_urdf.replace(problematic_path, correct_path)
                changes_made += 1
                self.get_logger().debug(f'Replaced: {problematic_path} -> {correct_path}')
        
        # Also handle generic package:// URIs for zed_msgs
        package_uri_pattern = r'package://zed_msgs/meshes/([^"\'>\s]+)'
        
        def replace_package_uri(match):
            nonlocal changes_made
            mesh_filename = match.group(1)
            
            # Find correct path for this mesh file
            for correct_path_base in ['/opt/ros/jazzy/share/zed_msgs/meshes/',
                                     '/root/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/',
                                     '/home/haito/haito_dev/ros2_ws/install/zed_msgs/share/zed_msgs/meshes/']:
                full_path = correct_path_base + mesh_filename
                if os.path.exists(full_path):
                    changes_made += 1
                    self.get_logger().debug(f'Package URI replaced: package://zed_msgs/meshes/{mesh_filename} -> file://{full_path}')
                    return f'file://{full_path}'
            
            # Fallback
            fallback_path = f'/opt/ros/jazzy/share/zed_msgs/meshes/{mesh_filename}'
            changes_made += 1
            self.get_logger().debug(f'Package URI replaced (fallback): package://zed_msgs/meshes/{mesh_filename} -> file://{fallback_path}')
            return f'file://{fallback_path}'
        
        modified_urdf = re.sub(package_uri_pattern, replace_package_uri, modified_urdf)
        
        if changes_made > 0:
            self.get_logger().info(f'Fixed {changes_made} mesh path references in robot description')
        
        return modified_urdf


def main(args=None):
    """Main entry point for the robot description remapper node."""
    rclpy.init(args=args)
    
    try:
        node = RobotDescriptionRemapper()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error in robot description remapper: {e}')
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
