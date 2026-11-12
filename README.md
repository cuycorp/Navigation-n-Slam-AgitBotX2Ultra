# Simulation of SLAM and navigation

For this task, a TurtleBot3 Burger was selected to map and navigate the TurtleBot3 House, an office-like world built for this robot, in a ROS 2 simulation that runs in Docker.

**Index**

- [Technology stack](#technology-stack)
- [Requirements](#requirements)
- [Install instructions](#install-instructions)
- [Available commands](#available-commands)
- [Tasks](#tasks)
  - [2.1 Setup](#21-setup)
  - [2.2 Mapping](#22-mapping)
  - [2.3 Navigation](#23-navigation)
  - [2.4 Precise arrival](#24-precise-arrival)
  - [2.5 Unexpected obstacle](#25-unexpected-obstacle)
- [Reproduce the 5 arrival runs](#reproduce-the-5-arrival-runs)
- [Exact versions](#exact-versions)
- [Repository layout](#repository-layout)

## Technology stack

| | Choice | Reason |
|---|---|---|
| Environment | **Docker** (Ubuntu 24.04 container) | ROS 2 isn't compatible with the development laptop's Ubuntu 25.10: Jazzy is only released for Ubuntu 24.04, so it runs in a container. Docker also makes the setup reproducible with one command on any Linux host |
| Robot | **TurtleBot3 Burger** | Standard ROS robot: 360° LiDAR (0.12–3.5 m, 5 Hz), wheel odometry and IMU. No camera to render, so it's lighter than the Waffle or the TurtleBot4 |
| World | **TurtleBot3 House** | Ships with the robot. Rooms, doors and furniture make it the most office-like stock world; the Nav2 depot and warehouse are open halls. The entrance plays "reception", and one room plays "meeting room" |
| ROS 2 | **Jazzy** | Long-term support until May 2029, and every package needed exists as a binary. Humble only pairs with older simulators, and Lyrical still lacks Nav2's main packages |
| Simulator | **Gazebo Harmonic** | The official pairing for Jazzy, with ready TurtleBot3 and Nav2 simulations |
| SLAM | **slam_toolbox** (online async) | Nav2's default: graph SLAM with loop closure, low CPU use, saves both the map and the pose graph |
| Navigation | **Nav2** (AMCL + Regulated Pure Pursuit) | The standard ROS 2 navigation stack. Regulated Pure Pursuit replaces the default MPPI controller, which is too heavy for a 4-core laptop |

## Requirements

ROS 2, Gazebo, the robot and the world all live in the Docker image, so the host only needs the items below. Tested on Ubuntu 25.10; other distributions supported by Docker should work, with two known exceptions this setup doesn't handle: **NVIDIA-only GPUs** (they need the NVIDIA Container Toolkit) and **SELinux hosts** such as Fedora or RHEL (they block the container's access to the X11 socket unless you add `security_opt: [label:disable]` to `compose.yaml`).

| Requirement | Notes |
|---|---|
| Linux x86_64, Docker Engine with Compose, GNU Make | Tested: Docker 29.4.0, Compose v5.1.2. Your user must be in the `docker` group |
| Display (X11 or XWayland) and `xhost` | For the Gazebo and RViz windows; `make up` runs `xhost +local:docker` |
| Intel or AMD GPU with OpenGL ≥ 3.3 at `/dev/dri` | Used through Mesa by Gazebo's renderer and simulated LiDAR. Integrated graphics are enough |
| ~2 GB free RAM, ~4 GB disk | Measured: 0.8 GiB RAM without the Gazebo window, 1.8 GiB with it; image 3.1 GB |
| Internet | For `make build` and the first `make sim` (Gazebo Fuel models) |

**Tested on:** Intel Core i7-8565U (4 cores), 14 GiB RAM, Intel UHD Graphics 620 (OpenGL 4.6), Ubuntu 25.10.

## Install instructions

1. Download the repository:

   ```bash
   git clone https://github.com/cuycorp/Navigation-n-Slam-AgitBotX2Ultra.git
   ```

2. Move into its folder. All the following commands run from here:

   ```bash
   cd Navigation-n-Slam-AgitBotX2Ultra
   ```

3. Build the Docker image `x2nav:jazzy` (ROS 2 Jazzy, Gazebo Harmonic and the TurtleBot3 packages). It prints the image size at the end. This is needed once, and again only if `docker/Dockerfile` changes:

   ```bash
   make build
   ```

4. Start the container in the background and allow its windows on your screen. Run this again after a reboot or a `make down`:

   ```bash
   make up
   ```

## Available commands

Run them from the repository folder. `make help` prints the same list.

| Command | Functionality | When to use it |
|---|---|---|
| `make help` | Lists the available targets | Whenever you forget a command |
| `make build` | Builds the Docker image and prints its size | Once after cloning, and after any change to `docker/Dockerfile` |
| `make up` | Starts the container and allows its windows on your screen | Before any other target, after a reboot or a `make down` |
| `make sim` | Starts the robot in the House world, with the Gazebo window | To see the simulated world (task 2.1) |
| `make sim GUI=0` | Same, without the Gazebo window, about twice as fast | For long runs, when you don't need to see the world |
| `make sim X=2.0 Y=-2.0` | Same, with the robot spawned at another point of the world (default: X=-2.0 Y=-0.5) | For the square test, which needs open floor |
| `make teleop` | Drives the robot with the keyboard (`i` forward, `j`/`l` turn, `k` stop) | To move the robot by hand, for example while mapping |
| `make rviz` | Opens RViz with the robot model, its frames, the LiDAR scan and odometry | To see what the robot senses |
| `make ws` | Builds our ROS 2 package `src/x2_nav` with colcon | After cloning, and after adding a node or changing `setup.py` |
| `make square` | Runs `square_driver`: drives a 1 m square without feedback and logs the start and end odometry | To test the first node and see odometry drift. Start the simulation with `make sim X=2.0 Y=-2.0` first |
| `make mapping GUI=0` | Starts the simulation, slam_toolbox and RViz, without the Gazebo window | To build the map (task 2.2), driving with `make auto-map` or `make teleop` |
| `make auto-map` | Drives the mapping route automatically, with smooth turns and a LiDAR safety stop (about 9–10 min) | Right after a fresh `make mapping`, with the robot at its spawn |
| `make save-map` | Saves the current map and pose graph to `maps/house.*` (`MAP=name` for another name) | When the map is complete, while `make mapping` is still running |
| `make nav GUI=0` | Starts the simulation, Nav2 on the saved map and RViz, without the Gazebo window | To send the robot to a goal (task 2.3) with RViz's "2D Goal Pose" |
| `make go` | Sends the robot to the meeting room with Nav2 and prints the result (`GOAL=reception` to go back) | While `make nav` is running, instead of clicking a goal in RViz |
| `make runs` | Drives 5 trips reception → meeting room and saves the arrival errors to `results/arrival_baseline.csv` | While `make nav` is running, to measure precise arrival (task 2.4) |
| `make shell` | Opens a terminal inside the container, with ROS 2 ready | To run `ros2` commands (topics, nodes) |
| `make log` | Shows the container's status, its CPU and RAM use, and the simulation processes running | To check what is running, or to measure resource use |
| `make stop` | Stops any simulation still running in the container | After closing a terminal without `Ctrl+C`. `make sim` runs it first |
| `make versions` | Prints the exact versions of the host, container, ROS 2 and Gazebo | To fill in or check the [Exact versions](#exact-versions) table |
| `make down` | Stops and removes the container (the image stays) | When you're done for the day, to free its memory |
| `make clean` | Removes the container and the image | To free 3 GB of disk, or to test a fresh install. The next start needs `make build` |

## Tasks

### 2.1 Setup

A TurtleBot3 Burger in the TurtleBot3 House world. Gazebo's physics step is set to 4 ms (`worlds/house.world`), which lets the simulation run at real-time speed on a laptop.

1. Start the simulation with the Gazebo window:

   ```bash
   make sim
   ```

   Or start it without the window, about twice as fast (real-time factor about 0.98 instead of 0.4–0.6):

   ```bash
   make sim GUI=0
   ```

2. In a second terminal, open a shell inside the container:

   ```bash
   make shell
   ```

3. Check that the robot's topics exist. You should see `/scan`, `/odom`, `/imu`, `/cmd_vel`, `/tf` and `/clock`, among others:

   ```bash
   ros2 topic list
   ```

4. Check that the LiDAR data reaches ROS. Expect about 5 Hz × the real-time factor, with regular gaps between messages. Press `Ctrl+C` to stop the measurement:

   ```bash
   ros2 topic hz /scan
   ```

5. Stop the simulation with `Ctrl+C` in its terminal. If you closed that terminal instead, run:

   ```bash
   make stop
   ```

#### Drive the robot and see its sensors

Start the simulation first (`make sim` or `make sim GUI=0`), then use one terminal per step.

1. Open RViz to see the robot model, its frames (`odom`, `base_footprint`, `base_scan`…), the LiDAR scan as red points, and the odometry arrows:

   ```bash
   make rviz
   ```

2. Drive the robot with the keyboard: `i` forward, `,` backward, `j` and `l` turn, `k` stop. The scan points should stay aligned with the walls while the robot moves. The simulated robot keeps its last command until it gets a new one, so always stop with `k` before quitting:

   ```bash
   make teleop
   ```

3. Build our ROS 2 package (`src/x2_nav`). Needed once after cloning, and after adding a node:

   ```bash
   make ws
   ```

4. Run the first node, `square_driver`. It drives a 1 m square without feedback, turning left, then prints the odometry pose at the start and at the end. The default spawn point is too tight for it (an obstacle 0.23 m to the left), so first restart the simulation at an open spot (1.7 m clear all around):

   ```bash
   make sim X=2.0 Y=-2.0
   ```

   Then, in another terminal:

   ```bash
   make square
   ```

   Compare the start and end poses in the log with the robot's true pose in Gazebo (Entity Tree → burger → Pose). Measured on 2026-11-09: true gap 0.9 cm and 1.0°; odometry gap 0.7 cm and 0.1°.

### 2.2 Mapping

Build a 2D map of the house with slam_toolbox while the robot drives a fixed route through the building (`config/map_route.yaml`). The map origin is the spawn point, which plays "reception". The saved map is already in `maps/`, so this section is only needed to rebuild it.

1. Start the simulation, slam_toolbox and RViz. The Gazebo window isn't needed: RViz shows the map as it grows:

   ```bash
   make mapping GUI=0
   ```

2. In a second terminal, once RViz shows the first scan, drive the route automatically. It takes about 9–10 minutes: the robot follows 153 waypoints, drives through the rounded corners without stopping, ramps up its turns, pauses 3 s at a few points, and stops if anything comes within 0.2 m ahead:

   ```bash
   make auto-map
   ```

3. When the log prints `Route finished`, save the map in the same terminal. This writes `maps/house.pgm` and `maps/house.yaml` (the map) and `maps/house.posegraph` and `maps/house.data` (slam_toolbox's graph):

   ```bash
   make save-map
   ```

4. Stop everything with `Ctrl+C` in the first terminal.

Check the map in RViz before saving it. The rooms north and north-east of the hall are sometimes smeared, with walls drawn twice at an angle; this happened in 2 of 3 runs on the same route. If you see it, start again from step 1.

To drive by hand instead, replace step 2 with `make teleop` (`i` forward, `j`/`l` turn, `k` stop; click in that terminal first). Don't touch anything: a collision makes odometry wrong and distorts the map.

### 2.3 Navigation

Send the robot from "reception" (its spawn, the map origin) to the "meeting room", the south-east room with the two café tables, using Nav2 on the saved map. The named poses are in `config/goals.yaml`; the Nav2 settings are in `config/nav2.yaml`.

1. Start the simulation, Nav2 and RViz. The robot starts at reception and AMCL already knows it, so there is no initial pose to set:

   ```bash
   make nav GUI=0
   ```

2. Wait until the terminal prints `Managed nodes are active` and RViz shows the map, the costmaps and the robot.

3. In RViz, click **2D Goal Pose**, then click in the south-east room (meeting room: map x 7.7, y −1.8) and drag towards the tables, to the east, to set the heading.

4. Watch the robot: a blue line shows the planned path, and the robot follows it through the entrance door and the south-east room's door. It takes about 2 minutes. The terminal prints `Goal succeeded` when it arrives.

5. Stop everything with `Ctrl+C`.

If the robot spins in place or backs up, Nav2 is running its recovery behaviours; it usually continues on its own.

To send the goal with one command instead of RViz:

1. Start Nav2 as in step 1 above, and wait for `Managed nodes are active`:

   ```bash
   make nav GUI=0
   ```

2. In a second terminal, send the robot to the meeting room. The script waits until Nav2 is ready, sends the goal, prints the distance left while driving, and ends with the result:

   ```bash
   make go
   ```

3. When it prints `Goal "meeting_room": SUCCEEDED`, send it back to reception the same way:

   ```bash
   make go GOAL=reception
   ```

The goals are the named poses in `config/goals.yaml`.


### 2.4 Precise arrival

Measure how close the robot stops to the meeting-room goal. The error is measured against the robot's true pose from Gazebo, which `make nav` publishes on `/ground_truth` in the map frame. Nav2 never uses it; it is only for measuring.

1. Start Nav2 and wait for `Managed nodes are active`:

   ```bash
   make nav GUI=0
   ```

2. In a second terminal, check the ground truth. With the robot still at reception, it reads about x = 0.0, y = 0.0:

   ```bash
   make shell
   ```

   ```bash
   ros2 topic echo --once /ground_truth
   ```

3. Run the arrival runs, described in [Reproduce the 5 arrival runs](#reproduce-the-5-arrival-runs).


### 2.5 Unexpected obstacle

<!-- Q5.1: make obstacle -->

## Reproduce the 5 arrival runs

Each run drives the robot to reception, then to the meeting room, waits 2 s, and logs the true pose, AMCL's estimate and the goal. Five runs take about 12 minutes.

1. Start Nav2 and wait for `Managed nodes are active`. Don't run RViz goals or `make go` at the same time:

   ```bash
   make nav GUI=0
   ```

2. In a second terminal, start the runs. The terminal prints one line per run, then a table with the mean and the largest error:

   ```bash
   make runs
   ```

3. The results are saved in `results/arrival_baseline.csv`, one row per run. Columns: the true, AMCL and goal poses; the arrival error (true − goal) as dx, dy, distance and yaw; the localization error (AMCL − true); the stopping error (AMCL − goal); and the time of the trip.

To save under another name, or run another number of times, use `make runs OUT=name RUNS=3`. A plain `make runs` overwrites `results/arrival_baseline.csv`, so give tests their own name.

The settings in `config/nav2.yaml` are the tuned ones (Q4.3). `results/arrival_baseline.csv` was measured before tuning, `results/arrival_tuned.csv` after it, and `results/tuning_E1.csv` to `tuning_E4.csv` hold the 3-run tests of each tuning step. To measure the tuned settings again:

```bash
make runs OUT=arrival_tuned
```


## Exact versions

Measured with `make versions` on 2026-11-08.

| Component | Version |
|---|---|
| Host OS | Ubuntu 25.10 |
| Docker | 29.4.0 (Compose v5.1.2) |
| Container OS | Ubuntu 24.04.5 LTS |
| ROS 2 | Jazzy |
| Simulator | Gazebo Sim (Harmonic) 8.15.0 |
| `ros-jazzy-ros-gz-sim` | 1.0.24 |
| `ros-jazzy-turtlebot3-gazebo` | 2.3.7 |

## Repository layout

<!-- D.1 -->

