"""Q2.1: the simulation + slam_toolbox (online async) + RViz, to build a map while driving.

Usage (inside the container):
    ros2 launch /ws/launch/mapping.launch.py [gui:=false] [rviz:=false] [x_pose:=-2.0] [y_pose:=-0.5]
Drive with teleop in another terminal, then save with `make save-map`.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Files of this repository, found relative to this launch file.
REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
SIM_LAUNCH = os.path.join(REPO, 'launch', 'sim.launch.py')
SLAM_PARAMS = os.path.join(REPO, 'config', 'slam.yaml')
RVIZ_CONFIG = os.path.join(REPO, 'config', 'mapping.rviz')


def generate_launch_description():
    slam_launch = os.path.join(
        get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')

    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Open the Gazebo window'),
        DeclareLaunchArgument('rviz', default_value='true', description='Open RViz'),
        # Mapping starts at the spawn pose, which becomes the origin of the map ("reception").
        DeclareLaunchArgument('x_pose', default_value='-2.0', description='Robot spawn x in the world'),
        DeclareLaunchArgument('y_pose', default_value='-0.5', description='Robot spawn y in the world'),

        # 1. The simulation: Gazebo, the Burger, the ROS <-> Gazebo bridge.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(SIM_LAUNCH),
            launch_arguments={'gui': gui, 'x_pose': x_pose, 'y_pose': y_pose}.items(),
        ),
        # 2. slam_toolbox: builds /map from /scan and odometry, and publishes TF map -> odom.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch),
            launch_arguments={'use_sim_time': 'true', 'slam_params_file': SLAM_PARAMS}.items(),
        ),
        # 3. RViz: the map as it grows, the scan and the robot.
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', RVIZ_CONFIG],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(rviz),
        ),
    ])
