# Each README step is a make target. `make help` lists them.
DC := docker compose

# Host IDs passed to Docker: files stay yours; the GPU is reachable without root.
export USER_UID   := $(shell id -u)
export USER_GID   := $(shell id -g)
export VIDEO_GID  := $(or $(shell getent group video  | cut -d: -f3),44)
# No "render" group (older systems): fall back to your own group, so the two entries never clash.
export RENDER_GID := $(or $(shell getent group render | cut -d: -f3),$(USER_GID))

# Gazebo window on (1) or off (0): make sim GUI=0
GUI ?= 1
# Robot spawn position in the world. Default: the stock House spawn (the map origin, "reception").
# For the square test use an open spot: make sim X=2.0 Y=-2.0 (1.7 m clear all around, measured).
X ?= -2.0
Y ?= -0.5

# Simulation processes that can outlive a closed terminal. The [x] brackets stop pkill from
# matching its own command line.
SIM_PROCS := [r]os2 launch|[g]z sim|[p]arameter_bridge|[r]obot_state_publisher|[r]viz2|[s]quare_driver|[a]sync_slam_toolbox_node|[a]uto_map|[m]ap_server|[a]mcl|[p]lanner_server|[c]ontroller_server|[b]ehavior_server|[b]t_navigator|[v]elocity_smoother|[l]ifecycle_manager

# Name of the map files in maps/: make save-map MAP=house
MAP ?= house

# Run a command inside the container, with ROS 2 and our workspace (once built) sourced.
ROS = $(DC) exec dev bash -c 'source /opt/ros/jazzy/setup.bash; \
      [ -f install/setup.bash ] && source install/setup.bash; $(1)'

.PHONY: help build up down clean log stop shell versions sim teleop rviz ws square mapping auto-map save-map nav
help:      ## list the targets
	@grep -E '^[a-z-]+:.*## ' Makefile | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'
build:     ## build the Docker image and print its size
	$(DC) build
	docker images x2nav:jazzy
up:        ## start the container and allow its windows on your screen
	xhost +local:docker
	$(DC) up -d
down:      ## stop the container
	$(DC) down
clean:     ## remove the container and the image built here (next start needs make build)
	$(DC) down --rmi local
log:       ## status of the container, its CPU and RAM use, and the simulations running in it
	$(DC) ps -a
	@ids=$$($(DC) ps -q); \
	  if [ -n "$$ids" ]; then docker stats --no-stream $$ids; \
	    echo "Simulation processes:"; \
	    procs=$$($(DC) exec -T dev pgrep -af "$(SIM_PROCS)"); \
	    if [ -n "$$procs" ]; then echo "$$procs" | cut -c1-100; else echo "  none"; fi; \
	  else echo "No container running: make up"; fi
stop:      ## stop any simulation still running in the container (e.g. after closing a terminal)
	@$(DC) exec -T dev bash -c 'pkill -INT -f "$(SIM_PROCS)" && sleep 3; \
	  pkill -KILL -f "$(SIM_PROCS)"; echo "Simulation processes stopped."'
shell:     ## open a shell inside the container
	$(DC) exec dev bash
versions:  ## print the exact versions for the README
	@echo "Host: $$(lsb_release -ds) · $$(docker --version)"
	@$(call ROS,. /etc/os-release; echo "Container: $$PRETTY_NAME · ROS 2 $$ROS_DISTRO"; \
	  gz sim --version | head -1; dpkg-query -W ros-jazzy-turtlebot3-gazebo ros-jazzy-ros-gz-sim)
sim: stop  ## Q1.1: Burger in the House world (4 ms physics step). GUI=0: no window; X= Y=: spawn position
	$(call ROS,ros2 launch /ws/launch/sim.launch.py gui:=$(GUI) x_pose:=$(X) y_pose:=$(Y))
teleop:    ## Q1.2: drive the robot with the keyboard (/cmd_vel is TwistStamped here)
	$(call ROS,ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
	  -p stamped:=true -p frame_id:=base_footprint -p speed:=0.2 -p turn:=1.0 -p use_sim_time:=true)
rviz:      ## Q1.2: RViz with the robot, its frames, the LiDAR scan and odometry
	$(call ROS,rviz2 -d /ws/config/view.rviz --ros-args -p use_sim_time:=true)
ws:        ## Q1.2: build our ROS 2 package (src/x2_nav) with colcon
	$(call ROS,colcon build --symlink-install)
square:    ## Q1.2: run square_driver: a 1 m square, open loop (start with: make sim X=2.0 Y=-2.0)
	$(call ROS,ros2 run x2_nav square_driver --ros-args -p use_sim_time:=true)
mapping: stop  ## Q2.1: simulation + slam_toolbox + RViz; drive with make teleop. GUI=0: no Gazebo window
	$(call ROS,ros2 launch /ws/launch/mapping.launch.py gui:=$(GUI) x_pose:=$(X) y_pose:=$(Y))
auto-map:  ## Q2.1: drive the mapping route automatically, smooth turns (right after a fresh make mapping)
	$(call ROS,ros2 run x2_nav auto_map --ros-args -p use_sim_time:=true -p route_file:=/ws/config/map_route.yaml \
	  -p pass_through:=true -p angular_accel:=1.5)
save-map:  ## Q2.1: save the current map to maps/$(MAP).pgm/.yaml and the pose graph (make mapping must be running)
	$(call ROS,ros2 run nav2_map_server map_saver_cli -f /ws/maps/$(MAP) --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0 \
	  && ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: /ws/maps/$(MAP)}")
nav: stop  ## Q3.1: simulation + Nav2 on maps/$(MAP).yaml + RViz; send a goal with "2D Goal Pose". GUI=0: no Gazebo window
	$(call ROS,ros2 launch /ws/launch/navigation.launch.py gui:=$(GUI) map:=/ws/maps/$(MAP).yaml)
