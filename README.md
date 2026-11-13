# Simulation of SLAM and navigation

For this task, a TurtleBot3 Burger was selected to map and navigate the TurtleBot3 House, an office-like world built for this robot, in a ROS 2 simulation that runs in Docker.

## Index

- [System Requirements](#system-requirements)
- [Install instructions](#install-instructions)
- [Instructions to run the tasks](#instructions-to-run-the-tasks)
  - [2.1 Setup](#21-setup)
  - [2.2 Mapping](#22-mapping)
  - [2.3 Navigation](#23-navigation)
  - [2.4 Precise arrival](#24-precise-arrival)
  - [2.5 Unexpected obstacle](#25-unexpected-obstacle)
- [Exact versions](#exact-versions)
- [Repository layout](#repository-layout)
- [Available commands](#available-commands)

## System Requirements

ROS 2, Gazebo, the robot and the world all live in the Docker image, so the host only needs the items below.

| Requirement | Notes |
|---|---|
| Linux x86_64, Docker Engine with Compose, GNU Make | Tested: Docker 29.4.0, Compose v5.1.2. Your user must be in the `docker` group |
| Display (X11 or XWayland) and `xhost` | For the Gazebo and RViz windows; `make up` runs `xhost +local:docker` |
| Intel or AMD GPU with OpenGL ≥ 3.3 at `/dev/dri` | Used through Mesa by Gazebo's renderer and simulated LiDAR. Integrated graphics are enough |
| ~2 GB free RAM, ~4 GB disk | Measured: 0.8 GiB RAM without the Gazebo window, 1.8 GiB with it; image 3.15 GB |
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

3. Build the Docker image `x2nav:jazzy`. It contains the whole stack: ROS 2 Jazzy, the Gazebo Harmonic simulator, the TurtleBot3 robot and House world, slam_toolbox for mapping and Nav2 for navigation. Needed once:

   ```bash
   make build
   ```

4. Start the container and allow its windows on your screen. Run this again after a reboot:

   ```bash
   make up
   ```

5. Build this repository's ROS 2 package (`src/x2_nav`: the mapping route driver, the goal sender, the measurement nodes). Needed once:

   ```bash
   make ws
   ```

## Instructions to run the tasks

Each task starts its own simulation. Stop it with `Ctrl+C` in its first terminal before starting the next task.

### 2.1 Setup

A TurtleBot3 Burger in the TurtleBot3 House world.

1. Start the simulation with the Gazebo window, to see the robot in the house:

   ```bash
   make sim
   ```

2. In a second terminal, print the exact versions of the host, the container, ROS 2 and Gazebo:

   ```bash
   make versions
   ```

### 2.2 Mapping

Build a map of the house with slam_toolbox while the robot drives a fixed route. The map already saved in `maps/` was made this way, so this is only needed to rebuild it.

1. Start the simulation, slam_toolbox and RViz, which shows the map as it grows:

   ```bash
   make mapping GUI=0
   ```

2. In a second terminal, drive the mapping route automatically. It takes about 10 minutes and ends with `Route finished`:

   ```bash
   make auto-map
   ```

3. Save the map to `maps/house.pgm` and `maps/house.yaml`:

   ```bash
   make save-map
   ```

Check the map in RViz before saving: if the north-east rooms look smeared (walls drawn twice), start again from step 1.

### 2.3 Navigation

Send the robot from "reception" (its start point) to the "meeting room" (the south-east room) with Nav2, on the saved map.

1. Start the simulation, Nav2 and RViz. Wait until the terminal prints `Managed nodes are active`:

   ```bash
   make nav GUI=0
   ```

2. In a second terminal, send the robot to the meeting room. It drives there in about 80 s, then prints `Goal "meeting_room": SUCCEEDED`:

   ```bash
   make go
   ```

### 2.4 Precise arrival

Measure, 5 times, how far from the meeting-room goal the robot stops, against its true pose from Gazebo.

1. Start Nav2 and wait for `Managed nodes are active`:

   ```bash
   make nav GUI=0
   ```

2. In a second terminal, run the 5 trips. It takes about 12 minutes, prints one line per run, then a table with the mean and the largest errors, and saves them to `results/check.csv`. The measured results are in `results/arrival_baseline.csv` (before tuning) and `results/arrival_tuned.csv` (after):

   ```bash
   make runs OUT=check
   ```

### 2.5 Unexpected obstacle

Drop a box that isn't in the map on the robot's path, and watch Nav2 drive around it.

1. Start Nav2 and wait for `Managed nodes are active`:

   ```bash
   make nav GUI=0
   ```

2. In a second terminal, send the robot to the meeting room:

   ```bash
   make go
   ```

3. In a third terminal, about 20 s later, when the robot has gone through the entrance door, drop the box 2 m ahead of it. In RViz the box appears in the costmaps, the path bends around it, and `make go` still ends with `SUCCEEDED`:

   ```bash
   make obstacle
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
| `make obstacle` | Drops a 0.3 m box on the path to the meeting room (`OX= OY=` for another place, map coordinates) | During `make go`, to test an unexpected obstacle (task 2.5) |
| `make block-door` | Blocks the meeting room's only door with a 1.4 m panel | To see Nav2's recoveries and a failed goal |
| `make clear-obstacle` | Removes the box and the panel from the simulation | After an obstacle test |
| `make shell` | Opens a terminal inside the container, with ROS 2 ready | To run `ros2` commands (topics, nodes) |
| `make log` | Shows the container's status, its CPU and RAM use, and the simulation processes running | To check what is running, or to measure resource use |
| `make stop` | Stops any simulation still running in the container | After closing a terminal without `Ctrl+C`. `make sim` runs it first |
| `make versions` | Prints the exact versions of the host, container, ROS 2 and Gazebo | To fill in or check the [Exact versions](#exact-versions) table |
| `make down` | Stops and removes the container (the image stays) | When you're done for the day, to free its memory |
| `make clean` | Removes the container and the image | To free 3 GB of disk, or to test a fresh install. The next start needs `make build` |
