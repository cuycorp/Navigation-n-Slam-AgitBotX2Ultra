"""Q4.1: publish the robot's true pose from Gazebo, in the map frame, on /ground_truth.

For measuring only: nothing in the navigation stack subscribes to it.

Input: /gz_poses (tf2_msgs/TFMessage), bridged from Gazebo's /world/default/dynamic_pose/info by
launch/navigation.launch.py. The bridge drops the entity names; the first transform is the
Burger model in the world frame (the only dynamic model in the House world), the others are its
links relative to it.

The map frame is the world frame shifted to the spawn pose, because mapping started there
(config/goals.yaml: reception = map origin = world (-2.0, -0.5)).
"""
import math

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


def yaw_from_quaternion(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class GroundTruth(Node):
    def __init__(self):
        super().__init__('ground_truth')
        # Spawn pose in the world = origin of the map (Makefile X, Y; mapping started there).
        self.declare_parameter('spawn_x', -2.0)
        self.declare_parameter('spawn_y', -0.5)
        self.declare_parameter('spawn_yaw', 0.0)
        self.sx = self.get_parameter('spawn_x').value
        self.sy = self.get_parameter('spawn_y').value
        self.syaw = self.get_parameter('spawn_yaw').value

        self.pub = self.create_publisher(PoseStamped, 'ground_truth', 10)
        self.create_subscription(TFMessage, 'gz_poses', self.on_poses, 10)

    def on_poses(self, msg):
        if not msg.transforms:
            return
        robot = msg.transforms[0].transform          # the Burger model, world frame
        wx = robot.translation.x - self.sx
        wy = robot.translation.y - self.sy
        c, s = math.cos(-self.syaw), math.sin(-self.syaw)
        yaw = yaw_from_quaternion(robot.rotation) - self.syaw

        out = PoseStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'map'
        out.pose.position.x = c * wx - s * wy
        out.pose.position.y = s * wx + c * wy
        out.pose.orientation.z = math.sin(yaw / 2.0)
        out.pose.orientation.w = math.cos(yaw / 2.0)
        self.pub.publish(out)


def main():
    rclpy.init()
    node = GroundTruth()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
