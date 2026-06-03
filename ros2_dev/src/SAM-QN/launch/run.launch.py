from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition, LaunchConfigurationEquals
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterFile
import os
import yaml

def generate_launch_description():

    fast_lio_dir = get_package_share_directory('sam-qn')
    config_path = os.path.join(fast_lio_dir, 'config', 'config.yaml')  
    
    with open(config_path, 'r') as file:
        configParams = yaml.safe_load(file)['sam-qn_node']['ros__parameters']   
    
    return LaunchDescription([
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz_sam',
            arguments=['-d', PathJoinSubstitution([
                FindPackageShare('sam-qn'),
                'rviz',
                'sam_rviz.rviz'
            ])],
            prefix='nice',
            output='screen'
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz_lio',
            arguments=['-d', PathJoinSubstitution([
                FindPackageShare('sam-qn'),
                'rviz',
                'lio_rviz.rviz'
            ])],
            prefix='nice',
            output='screen'
        ),

        Node(
            package='sam-qn',
            executable='sam-qn_node',
            name='sam_qn_node',
            output='screen',
            parameters=[configParams],
            remappings=[
                ('/Odometry', '/aft_mapped_to_init'),
                ('/cloud_registered', '/cloud_registered')
            ]
        ),
        
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('point_lio'),
                    'launch',
                    'mapping_unilidar_l1.launch.py'
                ])
            ]),
            launch_arguments={'rviz': 'false'}.items(),
        )
    ])