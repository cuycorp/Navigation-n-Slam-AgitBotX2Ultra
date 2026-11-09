"""Q1.2: first node. Drives a square, open loop, by publishing velocity commands on /cmd_vel.

Open loop = no feedback: the node drives straight for a computed time, turns for a computed
time, four times, and trusts the robot to follow. It logs the odometry pose at the start and
at the end, so you can see how far from its start the robot thinks it is (and compare with
the true pose in Gazebo). That gap is drift, and it comes back in Q4 (precise arrival).

Run (inside the container, simulation running):
    ros2 run x2_nav square_driver --ros-args -p use_sim_time:=true
"""
import math

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


class SquareDriver(Node):

    def __init__(self):
        super().__init__('square_driver')

        # Parameters: no topic names or numbers hard-coded in the logic (plan rule).
        self.declare_parameter('cmd_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('side', 1.0)           # m, length of one side
        self.declare_parameter('linear_speed', 0.1)   # m/s (Burger max is about 0.22)
        self.declare_parameter('angular_speed', 0.5)  # rad/s

        self.side = self.get_parameter('side').value
        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value

        # Time needed for each motion, at constant speed: time = distance / speed.
        self.forward_s = self.side / self.linear_speed             # 1.0 / 0.1 = 10 s
        self.turn_s = (math.pi / 2) / self.angular_speed           # 1.571 / 0.5 = 3.14 s
        self.segment_s = self.forward_s + self.turn_s              # one side + one corner

        # /cmd_vel is TwistStamped in this simulation (see turtlebot3_burger_bridge.yaml).
        self.pub = self.create_publisher(TwistStamped, self.get_parameter('cmd_topic').value, 10)
        self.create_subscription(Odometry, self.get_parameter('odom_topic').value, self.on_odom, 10)

        self.last_odom = None   # latest odometry pose, for the start/end log
        self.start_time = None  # set at the first timer tick with a valid clock
        self.done = False
        self.timer = self.create_timer(0.1, self.on_timer)  # 10 Hz, on simulation time

    def command_at(self, elapsed_s):
        """Return the command (linear m/s, angular rad/s) for `elapsed_s` seconds after the start.

        Return None once the square is finished.

        The square is 4 identical segments. Each segment lasts self.segment_s seconds:
          - first self.forward_s seconds: drive straight  -> (self.linear_speed, 0.0)
          - then  self.turn_s seconds:    turn left in place -> (0.0, self.angular_speed)
        After 4 segments: None.

        Example with the defaults (forward 10 s, turn 3.14 s, segment 13.14 s):
          elapsed  5.0 -> (0.1, 0.0)     side 1, driving
          elapsed 11.0 -> (0.0, 0.5)     corner 1, turning
          elapsed 14.0 -> (0.1, 0.0)     side 2, driving
          elapsed 53.0 -> None           done (4 × 13.14 = 52.6 s)
        """
        segment = int(elapsed_s // self.segment_s)    # 0, 1, 2, 3 = which side we're on
        if segment >= 4:
            return None                               # all 4 sides and corners done
        into_segment = elapsed_s % self.segment_s     # seconds since this side started
        if into_segment < self.forward_s:
            return (self.linear_speed, 0.0)           # still driving the straight side
        return (0.0, self.angular_speed)              # side done: turn the corner

    def on_odom(self, msg):
        self.last_odom = msg.pose.pose

    def log_pose(self, label):
        if self.last_odom is None:
            self.get_logger().warn(f'{label}: no odometry received yet')
            return
        p, q = self.last_odom.position, self.last_odom.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.get_logger().info(f'{label}: x={p.x:.3f} m  y={p.y:.3f} m  yaw={math.degrees(yaw):.1f}°')

    def publish(self, linear, angular):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x = float(linear)
        msg.twist.angular.z = float(angular)
        self.pub.publish(msg)

    def on_timer(self):
        now = self.get_clock().now()
        if self.start_time is None:
            # With use_sim_time, the clock reads 0 until the first /clock message arrives.
            if now.nanoseconds == 0 or self.last_odom is None:
                return
            self.start_time = now
            self.log_pose('Start (odometry)')

        elapsed_s = (now - self.start_time).nanoseconds * 1e-9
        command = self.command_at(elapsed_s)
        if command is None:
            self.publish(0.0, 0.0)  # stop the robot
            self.log_pose('End   (odometry)')
            self.done = True
            return
        self.publish(*command)


def main():
    rclpy.init()
    node = SquareDriver()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.publish(0.0, 0.0)  # never leave the robot driving
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
