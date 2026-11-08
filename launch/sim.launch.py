"""Q1.1: TurtleBot3 Burger in the House world, with a 4 ms physics step.

Same as turtlebot3_gazebo's launch/turtlebot3_house.launch.py (2.3.7), except:
  - the world is our copy, worlds/house.world (physics step 1 ms -> 4 ms, see P-007);
  - the Gazebo window is optional: gui:=false runs the simulation without it.

Usage (inside the container):  ros2 launch /ws/launch/sim.launch.py [gui:=false] [x_pose:=-2.0] [y_pose:=-0.5]
Later launch files (mapping, navigation) include this one as their first part.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

# Our world file, found relative to this launch file: <repo>/worlds/house.world
WORLD = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'worlds', 'house.world'))


def generate_launch_description():
    tb3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    tb3_launch = os.path.join(tb3_gazebo, 'launch')
    gz_sim_launch = os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')

    gui = LaunchConfiguration('gui')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Open the Gazebo window (true/false)'),
        # Spawn pose: the stock House launch's defaults. Mapping starts here, so it becomes the map origin.
        DeclareLaunchArgument('x_pose', default_value='-2.0', description='Robot spawn x in the world'),
        DeclareLaunchArgument('y_pose', default_value='-0.5', description='Robot spawn y in the world'),

        # Lets Gazebo find model://turtlebot3_house (the house itself) and the robot models.
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', os.path.join(tb3_gazebo, 'models')),

        # 1. Gazebo server: physics and sensors, running our world (-r: start unpaused).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_sim_launch),
            launch_arguments={'gz_args': f'-r -s -v2 {WORLD}', 'on_exit_shutdown': 'true'}.items(),
        ),
        # 2. Gazebo window: only when gui:=true.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_sim_launch),
            launch_arguments={'gz_args': '-g -v2', 'on_exit_shutdown': 'true'}.items(),
            condition=IfCondition(gui),
        ),
        # 3. robot_state_publisher: robot model and fixed frames (reused from turtlebot3_gazebo).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(tb3_launch, 'robot_state_publisher.launch.py')),
            launch_arguments={'use_sim_time': 'true'}.items(),
        ),
        # 4 + 5. Spawn the Burger and start the ROS <-> Gazebo bridge (reused from turtlebot3_gazebo).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(tb3_launch, 'spawn_turtlebot3.launch.py')),
            launch_arguments={'x_pose': x_pose, 'y_pose': y_pose}.items(),
        ),
    ])
