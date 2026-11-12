"""Q3.1: the simulation + Nav2 on the saved map + RViz, to send the robot to a goal.

Usage (inside the container):
    ros2 launch /ws/launch/navigation.launch.py [gui:=false] [rviz:=false] [map:=/ws/maps/house.yaml]
Then send a goal with RViz's "2D Goal Pose" tool.

Nav2's own bringup package is not used: it pulls in 629 MB of extras (Q3.1). This file starts the
same servers directly, with config/nav2.yaml.
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Files of this repository, found relative to this launch file.
REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
SIM_LAUNCH = os.path.join(REPO, 'launch', 'sim.launch.py')
NAV2_PARAMS = os.path.join(REPO, 'config', 'nav2.yaml')
DEFAULT_MAP = os.path.join(REPO, 'maps', 'house.yaml')
RVIZ_CONFIG = os.path.join(REPO, 'config', 'navigation.rviz')

# Nav2 servers started below, in the order the lifecycle manager brings them up.
NAV2_NODES = ['map_server', 'amcl', 'planner_server', 'controller_server',
              'behavior_server', 'bt_navigator', 'velocity_smoother']


def generate_launch_description():
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    map_file = LaunchConfiguration('map')
    sim_time = {'use_sim_time': True}

    def nav2_node(package, executable, remappings=(), extra=None):
        return Node(package=package, executable=executable, name=executable, output='screen',
                    parameters=[NAV2_PARAMS, sim_time, extra or {}], remappings=list(remappings))

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Open the Gazebo window'),
        DeclareLaunchArgument('rviz', default_value='true', description='Open RViz'),
        DeclareLaunchArgument('map', default_value=DEFAULT_MAP, description='Map yaml file'),

        # 1. The simulation, with the robot at its default spawn = reception = map origin.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(SIM_LAUNCH),
            launch_arguments={'gui': gui}.items(),
        ),
        # 2. Localization: the saved map, and AMCL (publishes TF map -> odom).
        nav2_node('nav2_map_server', 'map_server', extra={'yaml_filename': map_file}),
        nav2_node('nav2_amcl', 'amcl'),
        # 3. Planning and control: global path (NavFn), path following (Regulated Pure Pursuit),
        #    recoveries (spin, back up, wait), and the behaviour tree that ties them together.
        nav2_node('nav2_planner', 'planner_server'),
        nav2_node('nav2_controller', 'controller_server', remappings=[('cmd_vel', 'cmd_vel_nav')]),
        nav2_node('nav2_behaviors', 'behavior_server', remappings=[('cmd_vel', 'cmd_vel_nav')]),
        nav2_node('nav2_bt_navigator', 'bt_navigator'),
        # 4. Velocity smoother: limits speed and acceleration, then drives the robot on /cmd_vel.
        nav2_node('nav2_velocity_smoother', 'velocity_smoother',
                  remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')]),
        # 5. Lifecycle manager: configures and activates the servers above, in order.
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[sim_time, {'autostart': True, 'node_names': NAV2_NODES}]),
        # 6. RViz: map, costmaps, planned path, robot; goals with "2D Goal Pose".
        Node(package='rviz2', executable='rviz2', arguments=['-d', RVIZ_CONFIG],
             parameters=[sim_time], condition=IfCondition(rviz)),
    ])
