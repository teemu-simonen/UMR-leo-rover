import os
import yaml
from ament_index_python import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    rosbag_path_arg = DeclareLaunchArgument(
        'bag',
        description='Absolute path to the rosbag folder you want to process'
    )

    leo_rover_dir = get_package_share_directory('leo_rover_mapping')

    play_rosbag = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', LaunchConfiguration('bag'), '-r', '0.5'],
        output = 'screen'
    )

    mapping_config_path = os.path.join(leo_rover_dir, 'config', 'mapping.yaml')
    with open(mapping_config_path, 'r') as file:
        mappingConfigParams = yaml.safe_load(file)['sam_qn_node']['ros__parameters']
        
    mappingConfigParams['use_sim_time'] = False

    mapping_node = Node(
        package='sam-qn',
        executable='sam-qn_node',
        name='sam_qn_node',
        output='screen',
        parameters=[mappingConfigParams],
        remappings=[
            ('/Odometry', '/aft_mapped_to_init'),
            ('/cloud_registered', '/cloud_registered')
        ]
    )

    lioParams = [
        PathJoinSubstitution([FindPackageShare('leo_rover_mapping'), 'config', 'unilidar_l2.yaml']),
        {
            'use_sim_time': False,
            'use_imu_as_input': False,  
            'prop_at_freq_of_imu': True,
            'check_satu': True,
            'init_map_size': 10,
            'point_filter_num': 1,  
            'space_down_sample': True,
            'filter_size_surf': 0.1,  
            'filter_size_map': 0.1,  
            'cube_side_length': 1000.0,  
            'runtime_pos_log_enable': False,  
        }
    ]

    lio_node = Node(
        package='point_lio',
        executable='pointlio_mapping',
        name='laserMapping',
        output='screen',
        parameters=lioParams,
    )

    exporter_node = Node(
        package='leo_rover_mapping',
        executable='data_exporter.py',
        name='unified_exporter_node',
        output='screen',
        parameters=[{'use_sim_time': False}]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz_sam',
        arguments=['-d', PathJoinSubstitution([
            FindPackageShare('leo_rover_mapping'),
            'rviz', 'sam.rviz'
        ])],
        prefix='nice',
        output='screen',
        parameters=[{'use_sim_time': False}]
    )

    shutdown_event = RegisterEventHandler(
        OnProcessExit(
            target_action=play_rosbag,
            on_exit=[
                EmitEvent(event=Shutdown(reason='Rosbag processing complete. Shutting down SLAM.'))
            ]
        )
    )

    return LaunchDescription([
        rosbag_path_arg,
        play_rosbag,
        mapping_node,
        lio_node,
        exporter_node,
        rviz_node,
        shutdown_event,
    ])