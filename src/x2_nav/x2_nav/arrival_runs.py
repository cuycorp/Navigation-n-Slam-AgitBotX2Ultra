"""Q4.2: measure the arrival error at the meeting room over several runs, and save it as CSV.

Each run: drive to reception, drive to the meeting room (timed), wait 2 s, then log
the true pose (/ground_truth, Q4.1), AMCL's estimate (/amcl_pose) and the goal.
The return trip is driven, not teleported, so AMCL stays consistent.

Usage (inside the container, with `make nav` running):
    ros2 run x2_nav arrival_runs [name] [runs] --ros-args -p use_sim_time:=true
or: make runs                     (5 runs -> results/arrival_baseline.csv)
    make runs OUT=arrival_tuned   (Q4.3)

Errors, all in the map frame:
    arrival      = ground truth - goal   (what the brief asks: target 5 cm and 5 deg)
    localization = AMCL - ground truth   (how wrong the robot's own estimate is)
    stopping     = AMCL - goal           (how far from the goal the robot *thinks* it stopped)
"""
import csv
import math
import os
import sys

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.utilities import remove_ros_args

from x2_nav.go_to import make_pose

GOALS_FILE = '/ws/config/goals.yaml'
RESULTS_DIR = '/ws/results'
START, GOAL = 'reception', 'meeting_room'
SETTLE_S = 2.0


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def xy_yaw(pose):
    q = pose.orientation
    yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
    return pose.position.x, pose.position.y, yaw


def error(a, b):
    """(dx, dy, distance in cm, yaw difference in degrees) of pose a minus pose b."""
    dx, dy = a[0] - b[0], a[1] - b[1]
    return dx, dy, 100.0 * math.hypot(dx, dy), math.degrees(wrap(a[2] - b[2]))


class ArrivalRuns:
    def __init__(self, navigator):
        self.nav = navigator
        self.truth = None
        self.amcl = None
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        navigator.create_subscription(PoseStamped, 'ground_truth',
                                      lambda m: setattr(self, 'truth', xy_yaw(m.pose)), 10)
        navigator.create_subscription(PoseWithCovarianceStamped, 'amcl_pose',
                                      lambda m: setattr(self, 'amcl', xy_yaw(m.pose.pose)), latched)

    def sim_now(self):
        return self.nav.get_clock().now().nanoseconds / 1e9

    def drive(self, goal):
        """Drive to goal = [x, y, yaw]; return (TaskResult, duration in simulated seconds)."""
        start = self.sim_now()
        self.nav.goToPose(make_pose(self.nav, *goal))
        while not self.nav.isTaskComplete():
            pass
        return self.nav.getResult(), self.sim_now() - start

    def settle(self, seconds):
        end = self.sim_now() + seconds
        while self.sim_now() < end:
            rclpy.spin_once(self.nav, timeout_sec=0.1)


def main():
    rclpy.init()
    args = remove_ros_args(sys.argv)[1:]
    name = args[0] if args else 'arrival_baseline'
    runs = int(args[1]) if len(args) > 1 else 5
    with open(GOALS_FILE) as f:
        goals = yaml.safe_load(f)
    goal = goals[GOAL]

    navigator = BasicNavigator(node_name='arrival_runs')
    navigator.waitUntilNav2Active(localizer='robot_localization')   # don't reset AMCL (see go_to)
    exp = ArrivalRuns(navigator)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name + '.csv')
    rows = []
    for run in range(1, runs + 1):
        back, _ = exp.drive(goals[START])
        result, duration = exp.drive(goal)
        exp.settle(SETTLE_S)
        truth, amcl = exp.truth, exp.amcl
        if truth is None or amcl is None:
            print('No /ground_truth or /amcl_pose received: is make nav running?')
            break
        adx, ady, adist, ayaw = error(truth, goal)
        _, _, ldist, lyaw = error(amcl, truth)
        _, _, sdist, syaw = error(amcl, goal)
        rows.append({
            'run': run, 'result': result.name, 'return_result': back.name,
            'time_s': round(duration, 1),
            'goal_x': goal[0], 'goal_y': goal[1], 'goal_yaw_deg': round(math.degrees(goal[2]), 2),
            'truth_x': round(truth[0], 4), 'truth_y': round(truth[1], 4),
            'truth_yaw_deg': round(math.degrees(truth[2]), 2),
            'amcl_x': round(amcl[0], 4), 'amcl_y': round(amcl[1], 4),
            'amcl_yaw_deg': round(math.degrees(amcl[2]), 2),
            'arrival_dx_cm': round(100 * adx, 1), 'arrival_dy_cm': round(100 * ady, 1),
            'arrival_dist_cm': round(adist, 1), 'arrival_yaw_deg': round(ayaw, 1),
            'amcl_err_cm': round(ldist, 1), 'amcl_err_deg': round(lyaw, 1),
            'stop_err_cm': round(sdist, 1), 'stop_err_deg': round(syaw, 1),
        })
        r = rows[-1]
        print(f'Run {run}: {r["result"]}, {r["time_s"]} s, arrival {r["arrival_dist_cm"]} cm '
              f'{r["arrival_yaw_deg"]} deg, AMCL error {r["amcl_err_cm"]} cm', flush=True)
        with open(path, 'w', newline='') as f:              # rewrite after every run: nothing lost
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    print_table(rows, path)
    navigator.destroy_node()
    rclpy.shutdown()
    ok = rows and all(r['result'] == TaskResult.SUCCEEDED.name for r in rows)
    sys.exit(0 if ok else 1)


def print_table(rows, path):
    if not rows:
        return
    cols = [('run', 'Run'), ('arrival_dx_cm', 'dx (cm)'), ('arrival_dy_cm', 'dy (cm)'),
            ('arrival_dist_cm', 'Distance (cm)'), ('arrival_yaw_deg', 'Yaw error (°)'),
            ('amcl_err_cm', 'AMCL error (cm)'), ('time_s', 'Time (s)')]
    print(f'\nSaved {path}\n')
    print('| ' + ' | '.join(h for _, h in cols) + ' |')
    print('|' + '---|' * len(cols))
    for r in rows:
        print('| ' + ' | '.join(str(r[k]) for k, _ in cols) + ' |')
    for label, fn in (('Mean', lambda v: sum(v) / len(v)), ('Max', lambda v: max(v, key=abs))):
        cells = [label] + [f'{fn([r[k] for r in rows]):.1f}' for k, _ in cols[1:]]
        print('| ' + ' | '.join(cells) + ' |')


if __name__ == '__main__':
    main()
