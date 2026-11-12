"""Q2.1: drives the robot through a fixed route, so the map can be built without teleop.

For each waypoint of config/map_route.yaml: turn in place to face it, then drive to it, steering
with the odometry pose (closed loop). A waypoint written [x, y, seconds] also makes the robot stand
still there for that long, to give slam_toolbox time to close a loop (route options C and D).

Smooth driving (both off by default, used by route options D.1 and D.2):
- `pass_through`: don't stop at a waypoint when the next one is less than `reheading_limit` away in
  heading; keep driving and curve toward it. Rounded corners in the route file then give smooth turns.
- `angular_accel`: limit how fast the turn rate may change (rad/s^2), so no turn starts at full rate. The LiDAR is a safety stop: if anything is closer than
`stop_distance` in front while driving, the robot stops and the node aborts, because a collision
would corrupt the map (P-011).

This node only moves the robot. The map itself is built by slam_toolbox (`make mapping`).

Run (inside the container, right after a fresh `make mapping`, with the robot at its spawn):
    ros2 run x2_nav auto_map --ros-args -p use_sim_time:=true -p route_file:=/ws/config/map_route.yaml
"""
import math
import sys

import rclpy
import rclpy.duration
import yaml
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def wrap(angle):
    """Wrap an angle to [-pi, pi)."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def clamp(value, limit):
    return max(-limit, min(limit, value))


class AutoMap(Node):

    def __init__(self):
        super().__init__('auto_map')

        self.declare_parameter('route_file', '/ws/config/map_route.yaml')
        self.declare_parameter('cmd_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('linear_speed', 0.2)        # m/s (Burger max is about 0.22)
        self.declare_parameter('angular_speed', 0.8)       # rad/s
        self.declare_parameter('waypoint_tolerance', 0.10)  # m
        self.declare_parameter('heading_tolerance', 0.06)  # rad: stop turning, start driving
        self.declare_parameter('reheading_limit', 0.5)     # rad: while driving, go back to turning
        self.declare_parameter('stop_distance', 0.20)      # m: safety stop, in front of the LiDAR
        self.declare_parameter('front_half_angle', 20.0)   # deg: width of the safety sector
        self.declare_parameter('waypoint_timeout', 120.0)  # s of simulation time per waypoint
        self.declare_parameter('pass_through', False)      # don't stop at gentle corners
        self.declare_parameter('angular_accel', 0.0)       # rad/s^2, 0 = no limit

        get = lambda name: self.get_parameter(name).value
        self.linear_speed = get('linear_speed')
        self.angular_speed = get('angular_speed')
        self.waypoint_tolerance = get('waypoint_tolerance')
        self.heading_tolerance = get('heading_tolerance')
        self.reheading_limit = get('reheading_limit')
        self.stop_distance = get('stop_distance')
        self.front_half_angle = math.radians(get('front_half_angle'))
        self.waypoint_timeout = get('waypoint_timeout')
        self.pass_through = get('pass_through')
        self.angular_accel = get('angular_accel')
        self.last_angular = 0.0

        with open(get('route_file'), encoding='utf-8') as f:
            route = yaml.safe_load(f)
        # Odometry starts at zero at the spawn, with heading 0, so odom = world - spawn.
        sx, sy = route['spawn']
        # Each waypoint is [x, y] or [x, y, pause_seconds].
        self.waypoints = [(w[0] - sx, w[1] - sy) for w in route['waypoints']]
        self.pauses = [float(w[2]) if len(w) > 2 else 0.0 for w in route['waypoints']]
        self.stop_at = [self.is_stop(i) for i in range(len(self.waypoints))]

        self.pub = self.create_publisher(TwistStamped, get('cmd_topic'), 10)
        self.create_subscription(Odometry, get('odom_topic'), self.on_odom, 10)
        self.create_subscription(
            LaserScan, get('scan_topic'), self.on_scan, qos_profile_sensor_data)

        self.pose = None          # (x, y, yaw) from odometry
        self.front_range = None   # closest obstacle in the front sector, m
        self.index = 0
        self.turning = True       # True: turn in place. False: drive toward the waypoint.
        self.waypoint_start = None
        self.pause_until = None   # simulation time when the current pause ends
        self.finished = False
        self.failed = False
        self.create_timer(0.05, self.on_timer)  # 20 Hz, on simulation time

    def is_stop(self, i):
        """True if the robot must stop at waypoint i: last one, a pause, or a sharp corner."""
        if not self.pass_through or i == len(self.waypoints) - 1 or self.pauses[i] > 0.0 or i == 0:
            return True
        (x0, y0), (x1, y1), (x2, y2) = self.waypoints[i - 1], self.waypoints[i], self.waypoints[i + 1]
        turn = wrap(math.atan2(y2 - y1, x2 - x1) - math.atan2(y1 - y0, x1 - x0))
        return abs(turn) > self.reheading_limit

    def on_odom(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.pose = (p.x, p.y, yaw)

    def on_scan(self, msg):
        closest = math.inf
        for i, r in enumerate(msg.ranges):
            if math.isfinite(r) and abs(wrap(msg.angle_min + i * msg.angle_increment)) <= self.front_half_angle:
                closest = min(closest, r)
        self.front_range = closest

    def publish(self, linear, angular, limit=True):
        if limit and self.angular_accel > 0.0:
            step = self.angular_accel * 0.05   # the timer runs at 20 Hz
            angular = self.last_angular + clamp(angular - self.last_angular, step)
        self.last_angular = angular
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x = float(linear)
        msg.twist.angular.z = float(angular)
        self.pub.publish(msg)

    def stop(self, failed=False):
        self.publish(0.0, 0.0, limit=False)
        self.finished = True
        self.failed = failed

    def on_timer(self):
        now = self.get_clock().now()
        if self.finished or self.pose is None or self.front_range is None or now.nanoseconds == 0:
            return

        if self.pause_until is not None:
            if now < self.pause_until:
                self.publish(0.0, 0.0)
                return
            self.pause_until = None
            self.waypoint_start = now
            if self.index == len(self.waypoints):
                self.get_logger().info('Route finished. Save the map with: make save-map')
                self.stop()
                return

        if self.waypoint_start is None:
            self.waypoint_start = now
        if (now - self.waypoint_start).nanoseconds * 1e-9 > self.waypoint_timeout:
            self.get_logger().error(f'Waypoint {self.index + 1}: timeout, stopping')
            self.stop(failed=True)
            return

        x, y, yaw = self.pose
        target_x, target_y = self.waypoints[self.index]
        dx, dy = target_x - x, target_y - y
        distance = math.hypot(dx, dy)

        if distance < self.waypoint_tolerance:
            self.get_logger().info(
                f'Waypoint {self.index + 1}/{len(self.waypoints)} reached: odom x={x:.2f} y={y:.2f}')
            pause = self.pauses[self.index]
            stop_here = self.stop_at[self.index]
            self.index += 1
            self.turning = stop_here
            self.waypoint_start = now
            if not stop_here:
                return   # gentle corner: keep driving toward the next waypoint
            if pause > 0.0:
                self.pause_until = now + rclpy.duration.Duration(seconds=pause)
                self.publish(0.0, 0.0)
                return
            if self.index == len(self.waypoints):
                self.get_logger().info('Route finished. Save the map with: make save-map')
                self.stop()
            else:
                self.publish(0.0, 0.0)
            return

        heading_error = wrap(math.atan2(dy, dx) - yaw)

        if self.turning:
            if abs(heading_error) < self.heading_tolerance:
                self.turning = False
            else:
                turn = clamp(1.5 * heading_error, self.angular_speed)
                self.publish(0.0, math.copysign(max(abs(turn), 0.15), turn))
                return
        elif abs(heading_error) > self.reheading_limit:
            self.turning = True
            self.publish(0.0, 0.0)
            return

        if self.front_range < self.stop_distance:
            self.get_logger().error(
                f'Obstacle {self.front_range:.2f} m ahead on the way to waypoint {self.index + 1} '
                f'(odom x={x:.2f} y={y:.2f}): stopping')
            self.stop(failed=True)
            return

        if self.stop_at[self.index]:
            speed = min(self.linear_speed, max(0.08, 0.6 * distance))   # slow down before stopping
        else:
            speed = self.linear_speed
        self.publish(speed, clamp(1.5 * heading_error, 0.5))


def main():
    rclpy.init()
    node = AutoMap()
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.publish(0.0, 0.0)  # never leave the robot driving (P-009)
        failed = node.failed
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
