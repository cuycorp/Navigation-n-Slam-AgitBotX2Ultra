"""Q3.2: send the robot to a named goal from config/goals.yaml, with Nav2, and print the result.

Usage (inside the container, with `make nav` running):
    ros2 run x2_nav go_to meeting_room --ros-args -p use_sim_time:=true
or simply: make go GOAL=meeting_room

Exit code 0 if the goal succeeded, 1 otherwise, so scripts (Q4.2) can count successes.
"""
import math
import sys
import time

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.utilities import remove_ros_args

GOALS_FILE = '/ws/config/goals.yaml'


def make_pose(navigator, x, y, yaw):
    """A PoseStamped in the map frame, from [x, y, yaw] as written in goals.yaml."""
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def navigate(navigator, goals, goal_name):
    """Drive to goals[goal_name] and return the TaskResult (SUCCEEDED, CANCELED or FAILED).

    The initial pose is not set here. AMCL already starts at reception (set_initial_pose in
    config/nav2.yaml), and waitUntilNav2Active() with its default localizer='amcl' would publish
    (0, 0, 0) again before waiting: wrong when the robot is still in the meeting room from the
    previous run. localizer='robot_localization' skips that step and only waits for bt_navigator,
    which the lifecycle manager activates after AMCL.
    """
    navigator.waitUntilNav2Active(localizer='robot_localization')

    navigator.goToPose(make_pose(navigator, *goals[goal_name]))
    last_print = 0.0
    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback and time.monotonic() - last_print >= 5.0:    # every 5 s (wall clock)
            print(f'{feedback.distance_remaining:.2f} m to go', flush=True)
            last_print = time.monotonic()
    return navigator.getResult()


def main():
    rclpy.init()
    args = remove_ros_args(sys.argv)[1:]
    goal_name = args[0] if args else 'meeting_room'

    with open(GOALS_FILE) as f:
        goals = yaml.safe_load(f)
    if goal_name not in goals:
        print(f'Unknown goal "{goal_name}". Known goals: {", ".join(goals)}')
        sys.exit(2)

    navigator = BasicNavigator(node_name='go_to')
    result = navigate(navigator, goals, goal_name)
    print(f'Goal "{goal_name}": {result.name}')

    navigator.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if result == TaskResult.SUCCEEDED else 1)


if __name__ == '__main__':
    main()
